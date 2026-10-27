"""Exercise loading + completion logic for the auto-graded challenges feature."""

import json

from flask import g

from .database import get_db


def get_exercises_for_lesson(lesson_id):
    """Return all exercises for a lesson, with the current user's pass state."""
    db = get_db()
    user = getattr(g, "current_user", None)
    user_id = user["id"] if user else None

    rows = db.execute(
        """
        SELECT
            e.id, e.slug, e.title, e.prompt, e.starter_code,
            e.tests_json, e.hint, e.sort_order
        FROM lesson_exercises AS e
        WHERE e.lesson_id = ?
        ORDER BY e.sort_order, e.id
        """,
        (lesson_id,),
    ).fetchall()

    results = []
    for row in rows:
        passed = False
        if user_id is not None:
            done = db.execute(
                """
                SELECT 1 FROM user_exercise_results
                WHERE user_id = ? AND exercise_id = ?
                """,
                (user_id, row["id"]),
            ).fetchone()
            passed = done is not None

        results.append(
            {
                "id": row["id"],
                "slug": row["slug"],
                "title": row["title"],
                "prompt": row["prompt"],
                "starter_code": row["starter_code"],
                "tests": json.loads(row["tests_json"]),
                "hint": row["hint"],
                "sort_order": row["sort_order"],
                "passed": passed,
            }
        )

    return results


def get_exercise(exercise_id):
    """Fetch a single exercise, or None."""
    row = get_db().execute(
        """
        SELECT e.*, l.slug AS lesson_slug, m.slug AS module_slug
        FROM lesson_exercises AS e
        JOIN lessons AS l ON l.id = e.lesson_id
        JOIN modules AS m ON m.id = l.module_id
        WHERE e.id = ?
        """,
        (exercise_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "lesson_id": row["lesson_id"],
        "lesson_slug": row["lesson_slug"],
        "module_slug": row["module_slug"],
        "slug": row["slug"],
        "title": row["title"],
        "prompt": row["prompt"],
        "starter_code": row["starter_code"],
        "tests": json.loads(row["tests_json"]),
        "hint": row["hint"],
    }


def record_pass(user_id, exercise_id):
    """Record that a user passed an exercise. Idempotent."""
    db = get_db()
    db.execute(
        """
        INSERT OR IGNORE INTO user_exercise_results (user_id, exercise_id)
        VALUES (?, ?)
        """,
        (user_id, exercise_id),
    )
    db.commit()


def exercise_unlock_state(lesson_id):
    """Return a dict {exercise_id: is_unlocked} based on sequential completion.

    Rule: exercise 1 is always unlocked. Exercise N is unlocked if N-1 is passed.
    A passed exercise is always unlocked (even if an earlier one was skipped).
    """
    exercises = get_exercises_for_lesson(lesson_id)
    state = {}
    previous_passed = True  # first is always unlocked
    for ex in exercises:
        state[ex["id"]] = previous_passed or ex["passed"]
        previous_passed = ex["passed"]
    return state
