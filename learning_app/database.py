import json
import sqlite3
import psycopg2
import psycopg2.extras
import os
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


class PostgresWrapper:
    """Wraps psycopg2 to accept ? placeholders like SQLite."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, parameters=()):
        # Convert SQLite ? to Postgres %s
        query = query.replace("?", "%s")
        cur = self.conn.cursor()
        
        # SQLite uses cursor.lastrowid. Postgres requires RETURNING id.
        # If this is an INSERT without a RETURNING clause, add one so we can get the ID.
        if query.strip().upper().startswith("INSERT") and "RETURNING" not in query.upper():
            query += " RETURNING id"
            
        cur.execute(query, parameters)
        
        # If we added RETURNING id, fetch it and mock it as lastrowid
        if "RETURNING id" in query.upper():
            try:
                row = cur.fetchone()
                if row:
                    cur.lastrowid = row["id"]
            except Exception:
                pass
                
        return cur

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()

    def executescript(self, script):
        """Mimic SQLite's executescript for Postgres."""
        cur = self.conn.cursor()
        cur.execute(script)
        self.conn.commit()

def get_db():
    if "db" not in g:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            # --- POSTGRESQL (PRODUCTION) ---
            conn = psycopg2.connect(db_url)
            conn.cursor_factory = psycopg2.extras.DictCursor
            g.db = PostgresWrapper(conn)
        else:
            # --- SQLITE (LOCAL DEV) ---
            g.db = sqlite3.connect(current_app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def load_exercise_files(db):
    """Walk lessons/*/exercises.json and upsert each module's exercises."""
    lessons_dir = Path(__file__).resolve().parent.parent / "lessons"
    if not lessons_dir.exists():
        return

    for exercises_file in lessons_dir.glob("*/exercises.json"):
        module_slug = exercises_file.parent.name
        try:
            exercises_data = json.loads(exercises_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        for ex in exercises_data.get("exercises", []):
            lesson_slug = ex.get("lesson_slug")
            ex_slug = ex.get("slug")
            if not lesson_slug or not ex_slug:
                continue

            lesson_row = db.execute(
                """
                SELECT l.id FROM lessons AS l
                JOIN modules AS m ON m.id = l.module_id
                WHERE m.slug = ? AND l.slug = ?
                """,
                (module_slug, lesson_slug),
            ).fetchone()
            if not lesson_row:
                continue

            tests_json = json.dumps(ex.get("tests", []))
            
            # Postgres uses ON CONFLICT, SQLite uses INSERT OR REPLACE
            query = """
                INSERT INTO lesson_exercises
                    (lesson_id, slug, title, prompt, starter_code, tests_json, hint, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lesson_id, slug) DO UPDATE SET
                    title = excluded.title,
                    prompt = excluded.prompt,
                    starter_code = excluded.starter_code,
                    tests_json = excluded.tests_json,
                    hint = excluded.hint,
                    sort_order = excluded.sort_order
            """
            db.execute(
                query,
                (
                    lesson_row["id"],
                    ex_slug,
                    ex.get("title", ex_slug),
                    ex.get("prompt", ""),
                    ex.get("starter_code", ""),
                    tests_json,
                    ex.get("hint", ""),
                    ex.get("sort_order", 0),
                ),
            )
    db.commit()


def init_db():
    db = get_db()
    
    # 1. Create tables (safely, ignoring if they already exist)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS modules (
            id SERIAL PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            exercise TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE(module_id, slug)
        );

        CREATE TABLE IF NOT EXISTS progress (
            learner_id TEXT NOT NULL,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (learner_id, lesson_id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            display_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'learner' CHECK (role IN ('learner', 'admin')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            session_version INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, lesson_id)
        );

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tutor_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lesson_exercises (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            prompt TEXT NOT NULL DEFAULT '',
            starter_code TEXT NOT NULL DEFAULT '',
            tests_json TEXT NOT NULL DEFAULT '[]',
            hint TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE(lesson_id, slug)
        );

        CREATE TABLE IF NOT EXISTS user_exercise_results (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            exercise_id INTEGER NOT NULL REFERENCES lesson_exercises(id) ON DELETE CASCADE,
            passed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, exercise_id)
        );
    """)
    db.commit()

    # 2. Seed modules and lessons
    seed_file = Path(__file__).with_name("seed_content.json")
    if not seed_file.exists():
        return
        
    seed_modules = json.loads(seed_file.read_text(encoding="utf-8"))
    
    # Check if we already seeded
    existing = db.execute("SELECT COUNT(*) FROM modules").fetchone()
    if existing and existing[0] > 0:
        return

    for module_order, module in enumerate(seed_modules, start=1):
        query = """
            INSERT INTO modules (slug, title, description, sort_order)
            VALUES (?, ?, ?, ?)
        """
        if isinstance(db, PostgresWrapper):
            query += " RETURNING id"
            
        cur = db.execute(query, (module["slug"], module["title"], module.get("description", ""), module_order))
        
        if isinstance(db, PostgresWrapper):
            module_id = cur.fetchone()["id"]
        else:
            module_id = cur.lastrowid

        for lesson_order, lesson in enumerate(module.get("lessons", []), start=1):
            exercise_text = "\n".join(lesson.get("exercises", []))
            db.execute(
                """
                INSERT INTO lessons (module_id, slug, title, content, exercise, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (module_id, lesson["slug"], lesson["title"], lesson["content"], exercise_text, lesson_order),
            )

    db.commit()
    load_exercise_files(db)
