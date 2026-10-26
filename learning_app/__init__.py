import os
import secrets
from pathlib import Path

from flask import Flask, abort, request, session

from .database import close_db, init_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD"),
        DATABASE=os.path.join(app.instance_path, "learning_path.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
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
            submitted_token = request.form.get("csrf_token", "")
            expected_token = session.get("csrf_token", "")
            if not expected_token or not secrets.compare_digest(
                submitted_token, expected_token
            ):
                abort(400, description="The form expired. Please try again.")

    @app.context_processor
    def inject_template_helpers():
        def csrf_token():
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]

        return {
            "csrf_token": csrf_token,
            "is_admin": session.get("is_admin", False),
        }

    from .routes import bp

    app.register_blueprint(bp)
    with app.app_context():
        init_db()

    return app
