import json
import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
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
            id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY,
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
            completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (learner_id, lesson_id)
        );
        """
    )

    if db.execute("SELECT COUNT(*) FROM modules").fetchone()[0] == 0:
        seed_file = Path(__file__).with_name("seed_content.json")
        seed_modules = json.loads(seed_file.read_text(encoding="utf-8"))
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
                            lesson["exercise"],
                            lesson_order,
                        ),
                    )
