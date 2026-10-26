import hmac
import re
import unicodedata
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .database import get_db

bp = Blueprint("main", __name__)


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("main.admin_login"))
        return view(**kwargs)

    return wrapped_view


def make_slug(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug


def parse_exercises(value):
    exercises = []
    for line in value.splitlines():
        prompt = re.sub(r"^\s*(?:\d+[.)]\s*|[-*]\s*)", "", line).strip()
        if prompt:
            exercises.append(prompt)
    return exercises


def completed_lesson_ids():
    rows = get_db().execute(
        "SELECT lesson_id FROM progress WHERE learner_id = ?",
        (session["learner_id"],),
    ).fetchall()
    return {row["lesson_id"] for row in rows}


def get_module_or_404(slug):
    module = get_db().execute(
        "SELECT * FROM modules WHERE slug = ?", (slug,)
    ).fetchone()
    if module is None:
        abort(404)
    return module


@bp.get("/")
def index():
    db = get_db()
    modules = db.execute(
        """
        SELECT m.*, COUNT(l.id) AS lesson_count
        FROM modules AS m
        LEFT JOIN lessons AS l ON l.module_id = m.id
        GROUP BY m.id
        ORDER BY m.sort_order, m.id
        """
    ).fetchall()
    done = completed_lesson_ids()
    total_lessons = sum(module["lesson_count"] for module in modules)
    return render_template(
        "index.html",
        modules=modules,
        completed_count=len(done),
        total_lessons=total_lessons,
    )


@bp.get("/modules/<slug>")
def module_detail(slug):
    module = get_module_or_404(slug)
    lessons = get_db().execute(
        """
        SELECT * FROM lessons
        WHERE module_id = ?
        ORDER BY sort_order, id
        """,
        (module["id"],),
    ).fetchall()
    done = completed_lesson_ids()
    return render_template(
        "module.html", module=module, lessons=lessons, completed_ids=done
    )


@bp.get("/lessons/<int:lesson_id>")
def lesson_detail(lesson_id):
    lesson = get_db().execute(
        """
        SELECT l.*, m.title AS module_title, m.slug AS module_slug
        FROM lessons AS l
        JOIN modules AS m ON m.id = l.module_id
        WHERE l.id = ?
        """,
        (lesson_id,),
    ).fetchone()
    if lesson is None:
        abort(404)
    return render_template(
        "lesson.html",
        lesson=lesson,
        exercises=parse_exercises(lesson["exercise"]),
        is_completed=lesson_id in completed_lesson_ids(),
    )


@bp.get("/python-runner")
def python_runner():
    return render_template("python_runner.html")


@bp.post("/lessons/<int:lesson_id>/complete")
def mark_complete(lesson_id):
    db = get_db()
    if db.execute("SELECT 1 FROM lessons WHERE id = ?", (lesson_id,)).fetchone() is None:
        abort(404)
    db.execute(
        """
        INSERT OR IGNORE INTO progress (learner_id, lesson_id)
        VALUES (?, ?)
        """,
        (session["learner_id"], lesson_id),
    )
    db.commit()
    flash("Lesson marked as complete.", "success")
    return redirect(url_for("main.lesson_detail", lesson_id=lesson_id))


@bp.route("/admin/login", methods=("GET", "POST"))
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("main.admin_dashboard"))
    if request.method == "POST":
        expected_password = current_app.config.get("ADMIN_PASSWORD")
        submitted_password = request.form.get("password", "")
        if expected_password and hmac.compare_digest(
            submitted_password.encode("utf-8"), expected_password.encode("utf-8")
        ):
            session["is_admin"] = True
            flash("Signed in.", "success")
            return redirect(url_for("main.admin_dashboard"))
        flash("Sign-in failed. Check the configured admin password.", "error")
    return render_template("admin_login.html")


@bp.post("/admin/logout")
@admin_required
def admin_logout():
    session.pop("is_admin", None)
    flash("Signed out.", "success")
    return redirect(url_for("main.index"))


@bp.get("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    modules = db.execute(
        """
        SELECT m.*, COUNT(l.id) AS lesson_count
        FROM modules AS m
        LEFT JOIN lessons AS l ON l.module_id = m.id
        GROUP BY m.id
        ORDER BY m.sort_order, m.id
        """
    ).fetchall()
    lessons = db.execute(
        "SELECT id, module_id, title FROM lessons ORDER BY sort_order, id"
    ).fetchall()
    lessons_by_module = {}
    for lesson in lessons:
        lessons_by_module.setdefault(lesson["module_id"], []).append(lesson)
    return render_template(
        "admin_dashboard.html",
        modules=modules,
        lessons_by_module=lessons_by_module,
    )


@bp.route("/admin/modules/new", methods=("GET", "POST"))
@admin_required
def create_module():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        slug = make_slug(title)
        if not title or not slug:
            flash("Enter a title containing letters or numbers.", "error")
        else:
            db = get_db()
            duplicate = db.execute(
                "SELECT 1 FROM modules WHERE slug = ?", (slug,)
            ).fetchone()
            if duplicate:
                flash("A module with that title already exists.", "error")
            else:
                next_order = db.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM modules"
                ).fetchone()[0]
                db.execute(
                    """
                    INSERT INTO modules (slug, title, description, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (slug, title, description, next_order),
                )
                db.commit()
                flash("Module created. Add lessons from the content dashboard.", "success")
                return redirect(url_for("main.admin_dashboard"))
    return render_template("module_form.html", module=None)


@bp.route("/admin/modules/<int:module_id>/edit", methods=("GET", "POST"))
@admin_required
def edit_module(module_id):
    db = get_db()
    module = db.execute(
        "SELECT * FROM modules WHERE id = ?", (module_id,)
    ).fetchone()
    if module is None:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        slug = make_slug(title)
        duplicate = db.execute(
            "SELECT 1 FROM modules WHERE slug = ? AND id != ?",
            (slug, module_id),
        ).fetchone()
        if not title or not slug:
            flash("Enter a title containing letters or numbers.", "error")
        elif duplicate:
            flash("A module with that title already exists.", "error")
        else:
            db.execute(
                "UPDATE modules SET slug = ?, title = ?, description = ? WHERE id = ?",
                (slug, title, description, module_id),
            )
            db.commit()
            flash("Module updated.", "success")
            return redirect(url_for("main.admin_dashboard"))
    return render_template("module_form.html", module=module)


@bp.route("/admin/lessons/new", methods=("GET", "POST"))
@admin_required
def create_lesson():
    db = get_db()
    modules = db.execute(
        "SELECT id, title FROM modules ORDER BY sort_order, id"
    ).fetchall()
    if request.method == "POST":
        module_id = request.form.get("module_id", type=int)
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        exercise = "\n".join(parse_exercises(request.form.get("exercise", "")))
        slug = make_slug(title)
        module_exists = module_id is not None and db.execute(
            "SELECT 1 FROM modules WHERE id = ?", (module_id,)
        ).fetchone()
        if not title or not slug:
            flash("Enter a title containing letters or numbers.", "error")
        elif not module_exists:
            flash("Choose a valid module.", "error")
        else:
            duplicate = db.execute(
                "SELECT 1 FROM lessons WHERE module_id = ? AND slug = ?",
                (module_id, slug),
            ).fetchone()
            if duplicate:
                flash("A lesson with that title already exists in this module.", "error")
            else:
                next_order = db.execute(
                    """
                    SELECT COALESCE(MAX(sort_order), 0) + 1
                    FROM lessons WHERE module_id = ?
                    """,
                    (module_id,),
                ).fetchone()[0]
                db.execute(
                    """
                    INSERT INTO lessons
                        (module_id, slug, title, content, exercise, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (module_id, slug, title, content, exercise, next_order),
                )
                db.commit()
                flash("Lesson created.", "success")
                return redirect(url_for("main.admin_dashboard"))
    return render_template(
        "lesson_form.html",
        lesson=None,
        modules=modules,
        lesson_exercises="",
    )


@bp.route("/admin/lessons/<int:lesson_id>/edit", methods=("GET", "POST"))
@admin_required
def edit_lesson(lesson_id):
    db = get_db()
    lesson = db.execute(
        "SELECT * FROM lessons WHERE id = ?", (lesson_id,)
    ).fetchone()
    if lesson is None:
        abort(404)
    modules = db.execute(
        "SELECT id, title FROM modules ORDER BY sort_order, id"
    ).fetchall()
    if request.method == "POST":
        module_id = request.form.get("module_id", type=int)
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        exercise = "\n".join(parse_exercises(request.form.get("exercise", "")))
        slug = make_slug(title)
        module_exists = module_id is not None and db.execute(
            "SELECT 1 FROM modules WHERE id = ?", (module_id,)
        ).fetchone()
        duplicate = db.execute(
            """
            SELECT 1 FROM lessons
            WHERE module_id = ? AND slug = ? AND id != ?
            """,
            (module_id, slug, lesson_id),
        ).fetchone() if module_exists else None
        if not title or not slug:
            flash("Enter a title containing letters or numbers.", "error")
        elif not module_exists:
            flash("Choose a valid module.", "error")
        elif duplicate:
            flash("A lesson with that title already exists in this module.", "error")
        else:
            db.execute(
                """
                UPDATE lessons
                SET module_id = ?, slug = ?, title = ?, content = ?, exercise = ?
                WHERE id = ?
                """,
                (module_id, slug, title, content, exercise, lesson_id),
            )
            db.commit()
            flash("Lesson updated.", "success")
            return redirect(url_for("main.admin_dashboard"))
    return render_template(
        "lesson_form.html",
        lesson=lesson,
        modules=modules,
        lesson_exercises="\n".join(parse_exercises(lesson["exercise"])),
    )
