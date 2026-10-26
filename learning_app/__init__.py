import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, abort, g, request, session

from .database import close_db, get_db, init_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD"),
        ADMIN_DISPLAY_NAME=os.environ.get("ADMIN_DISPLAY_NAME", "Administrator"),
        DATABASE=os.path.join(app.instance_path, "learning_path.db"),
        MAIL_SERVER=os.environ.get("MAIL_SERVER"),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", "587")),
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
        MAIL_USE_TLS=os.environ.get("MAIL_USE_TLS", "true").lower() == "true",
        MAIL_DEFAULT_SENDER=os.environ.get("MAIL_DEFAULT_SENDER"),
        PUBLIC_BASE_URL=os.environ.get("PUBLIC_BASE_URL", "").rstrip("/"),
        OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY"),
        OPENAI_MODEL=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        MAX_CONTENT_LENGTH=256 * 1024,
        PERMANENT_SESSION_LIFETIME=timedelta(days=14),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)

    @app.before_request
    def prepare_session_and_check_csrf():
        session.permanent = True
        session.setdefault("learner_id", secrets.token_urlsafe(24))

        if request.method == "POST":
            submitted_token = (
                request.headers.get("X-CSRF-Token")
                or request.form.get("csrf_token", "")
            )
            expected_token = session.get("csrf_token", "")
            if not expected_token or not secrets.compare_digest(
                submitted_token, expected_token
            ):
                abort(400, description="The form expired. Please try again.")

        user_id = session.get("user_id")
        g.current_user = None
        if user_id is not None:
            user = get_db().execute(
                """
                SELECT id, display_name, email, role, session_version
                FROM users WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
            if (
                user is None
                or user["session_version"] != session.get("session_version")
            ):
                session.clear()
                session["learner_id"] = secrets.token_urlsafe(24)
            else:
                g.current_user = user

    @app.context_processor
    def inject_template_helpers():
        def csrf_token():
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]

        return {
            "csrf_token": csrf_token,
            "current_user": getattr(g, "current_user", None),
            "is_admin": (
                getattr(g, "current_user", None) is not None
                and g.current_user["role"] == "admin"
            ),
        }

    from .routes import bp

    app.register_blueprint(bp)
    with app.app_context():
        init_db()

    return app
