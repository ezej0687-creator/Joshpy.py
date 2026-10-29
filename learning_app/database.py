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


def init_db():
    db = get_db()
    db.executescript(
        """
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
            email TEXT NOT NULL UNIQUE ,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'learner'
                CHECK (role IN ('learner', 'admin')),
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

        CREATE INDEX IF NOT EXISTS idx_user_progress_lesson
            ON user_progress(lesson_id);
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_user
            ON password_reset_tokens(user_id);
        CREATE INDEX IF NOT EXISTS idx_tutor_requests_user_created
            ON tutor_requests(user_id, created_at);

        CREATE TABLE IF NOT EXISTS lesson_exercises (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            prompt TEXT NOT NULL,
            starter_code TEXT NOT NULL DEFAULT '',
            tests_json TEXT NOT NULL DEFAULT '[]',
            hint TEXT DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE(lesson_id, slug)
        );

        CREATE INDEX IF NOT EXISTS idx_lesson_exercises_lesson
            ON lesson_exercises(lesson_id);

        CREATE TABLE IF NOT EXISTS user_exercise_results (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            exercise_id INTEGER NOT NULL REFERENCES lesson_exercises(id) ON DELETE CASCADE,
            passed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, exercise_id)
        );
        """
    )
    admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().casefold()
    admin_password = current_app.config.get("ADMIN_PASSWORD") or ""
    if bool(admin_email) != bool(admin_password):
        raise RuntimeError(
            "Set both ADMIN_EMAIL and ADMIN_PASSWORD to bootstrap the first admin account."
        )
    if admin_password and len(admin_password) < 12:
        raise RuntimeError(
            "ADMIN_PASSWORD must contain at least 12 characters for the first admin account."
        )
    if (
        admin_email
        and admin_password
        and db.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        is None
    ):
        existing_email = db.execute(
            "SELECT role FROM users WHERE email = ?", (admin_email,)
        ).fetchone()
        if existing_email is not None:
            raise RuntimeError(
                "ADMIN_EMAIL already belongs to a non-admin account; configure "
                "a different email for the initial administrator."
            )
        db.execute(
            """
            INSERT INTO users
                (display_name, email, password_hash, role)
            VALUES (?, ?, ?, 'admin')
            """,
            (
                current_app.config.get("ADMIN_DISPLAY_NAME", "Administrator"),
                admin_email,
                generate_password_hash(admin_password),
            ),
        )
        db.commit()

    seed_file = Path(__file__).with_name("seed_content.json")
    seed_modules = json.loads(seed_file.read_text(encoding="utf-8"))

    if db.execute("SELECT COUNT(*) FROM modules").fetchone()[0] == 0:
        with db:
            for module_order, module in enumerate(seed_modules, start=1):
                cursor = db.execute(
                    """
                    INSERT INTO modules (slug, title, description, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        module["slug"],
                        module["title"],
                        module["description"],
                        module_order,
                    ),
                )
                for lesson_order, lesson in enumerate(module["lessons"], start=1):
                    db.execute(
                        """
                        INSERT INTO lessons
                            (module_id, slug, title, content, exercise, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cursor.lastrowid,
                            lesson["slug"],
                            lesson["title"],
                            lesson["content"],
                            "\n".join(lesson["exercises"]),
                            lesson_order,
                        ),
                    )

    command_module = seed_modules[0]
    if db.execute(
        "SELECT 1 FROM modules WHERE slug = ?", (command_module["slug"],)
    ).fetchone() is None:
        with db:
            db.execute("UPDATE modules SET sort_order = sort_order + 1")
            cursor = db.execute(
                """
                INSERT INTO modules (slug, title, description, sort_order)
                VALUES (?, ?, ?, 0)
                """,
                (
                    command_module["slug"],
                    command_module["title"],
                    command_module["description"],
                ),
            )
            for lesson_order, lesson in enumerate(command_module["lessons"], start=1):
                db.execute(
                    """
                    INSERT INTO lessons
                        (module_id, slug, title, content, exercise, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cursor.lastrowid,
                        lesson["slug"],
                        lesson["title"],
                        lesson["content"],
                        "\n".join(lesson["exercises"]),
                        lesson_order,
                    ),
                )
