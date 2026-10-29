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
    
    # In Postgres, we have to check if tables exist before creating them
    # because executescript is not fully supported.
    try:
        db.execute("SELECT 1 FROM modules LIMIT 1")
    except Exception:
        # Tables don't exist yet, create them
        schema = Path(__file__).with_name("schema.sql")
        if not schema.exists():
            raise RuntimeError("schema.sql not found")
        db.executescript(schema.read_text(encoding="utf-8"))
        db.commit()

    seed_file = Path(__file__).with_name("seed_content.json")
    if not seed_file.exists():
        return
        
    seed_modules = json.loads(seed_file.read_text(encoding="utf-8"))
    
    # Check if we already seeded
    existing = db.execute("SELECT COUNT(*) FROM modules").fetchone()
    if existing and existing[0] > 0:
        return

    for module_order, module in enumerate(seed_modules, start=1):
        # Use RETURNING id for Postgres
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
