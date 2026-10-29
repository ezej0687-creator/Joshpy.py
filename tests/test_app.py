import json
import sqlite3
import tempfile
import time
import unittest
from urllib.error import URLError
from pathlib import Path
from unittest.mock import MagicMock, patch

from learning_app import create_app


class LearningAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "ADMIN_EMAIL": "admin@example.test",
                "ADMIN_PASSWORD": "test-admin-password",
                "MAIL_SERVER": "mail.example.test",
                "MAIL_DEFAULT_SENDER": "learning@example.test",
                "PUBLIC_BASE_URL": "https://learning.example.test",
                "DATABASE": str(database_path),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf_token(self, client=None):
        client = client or self.client
        with client.session_transaction() as session:
            return session["csrf_token"]

    def register(self, client=None, display_name="Test Learner", email="learner@example.test"):
        client = client or self.client
        client.get("/register")
        return client.post(
            "/register",
            data={
                "csrf_token": self.csrf_token(client),
                "display_name": display_name,
                "email": email,
                "password": "a-very-secure-password",
                "password_confirmation": "a-very-secure-password",
            },
        )

    def sign_in_admin(self, client=None, password="test-admin-password"):
        client = client or self.client
        client.get("/login")
        return client.post(
            "/login",
            data={
                "csrf_token": self.csrf_token(client),
                "email": "admin@example.test",
                "password": password,
            },
        )

    def test_learning_path_and_lesson_progress(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")
        self.register()

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertLess(
            response.data.index(b"Command Line: Your Powerful Toolbox"),
            response.data.index(b"Python fundamentals"),
        )
        self.assertIn(b"Python fundamentals", response.data)

        self.client.get("/dashboard")
        lesson_response = self.client.get("/lessons/1")
        self.assertEqual(lesson_response.status_code, 200)
        self.assertEqual(lesson_response.data.count(b"data-practice-editor"), 1)
        self.assertIn(b">Run<", lesson_response.data)
        self.assertIn(b'sandbox="allow-scripts"', lesson_response.data)
        self.assertEqual(self.client.post(
            "/lessons/1/complete",
            data={"csrf_token": self.csrf_token()},
        ).status_code, 302)

        self.client.get("/dashboard")
        response = self.client.post(
            "/lessons/1/complete",
            data={"csrf_token": self.csrf_token()},
        )
        self.assertEqual(response.status_code, 302)

        dashboard = self.client.get("/dashboard")
        self.assertIn(b"1 of 30", dashboard.data)
        self.assertIn(b"Test Learner", dashboard.data)

    def test_learning_pages_require_sign_in_and_logout_returns_to_authentication(self):
        for path in ("/", "/modules/fundamentals", "/lessons/1", "/python-runner"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertEqual(response.headers["Location"], "/login", path)

        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertIn(b"create a new account", self.client.get("/login").data)
        self.register()
        self.client.get("/dashboard")

        logout_response = self.client.post(
            "/logout",
            data={"csrf_token": self.csrf_token()},
        )
        self.assertEqual(logout_response.status_code, 302)
        self.assertEqual(logout_response.headers["Location"], "/login")
        self.assertIn("no-store", logout_response.headers["Cache-Control"])

        login_page = self.client.get("/")
        self.assertEqual(login_page.status_code, 302)
        self.assertEqual(login_page.headers["Location"], "/login")
        login_page = self.client.get("/login")
        self.assertEqual(login_page.status_code, 200)
        self.assertIn(b"create a new account", login_page.data)
        self.assertIn(b"Sign up", login_page.data)

        admin_client = self.app.test_client()
        self.assertEqual(self.sign_in_admin(admin_client).status_code, 302)
        admin_client.get("/admin")
        admin_logout = admin_client.post(
            "/admin/logout",
            data={"csrf_token": self.csrf_token(admin_client)},
        )
        self.assertEqual(admin_logout.status_code, 302)
        self.assertEqual(admin_logout.headers["Location"], "/login")

    def test_completion_requires_csrf_token(self):
        response = self.client.post("/lessons/1/complete")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_tutor_requires_sign_in_and_shows_setup_when_not_configured(self):
        response = self.client.get("/tutor")
        self.assertEqual(response.status_code, 302)

        self.register()
        response = self.client.get("/tutor")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"OPENAI_API_KEY", response.data)
        self.assertNotIn(b"data-chat-form", response.data)

    def test_tutor_sends_bounded_lesson_context_to_openai(self):
        self.register()
        self.app.config["OPENAI_API_KEY"] = "test-openai-secret"
        self.client.get("/tutor")
        token = self.csrf_token()
        openai_response = MagicMock()
        openai_response.__enter__.return_value = openai_response
        openai_response.read.return_value = json.dumps(
            {
                "choices": [
                    {"message": {"content": "Let's work through it together."}}
                ]
            }
        ).encode("utf-8")
        with patch(
            "learning_app.routes.urlopen",
            return_value=openai_response,
        ) as openai_request:
            response = self.client.post(
                "/api/tutor",
                json={
                    "messages": [{"role": "user", "content": "Can you help me?"}],
                    "lesson_id": 1,
                },
                headers={"X-CSRF-Token": token},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"reply": "Let's work through it together."})
        request = openai_request.call_args.args[0]
        request_body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-openai-secret")
        self.assertEqual(request_body["model"], "gpt-4o-mini")
        self.assertEqual(request_body["messages"][1]["content"], "Can you help me?")
        self.assertIn("Course outline:", request_body["messages"][0]["content"])
        self.assertIn("Lesson material:", request_body["messages"][0]["content"])
        tutor_page = self.client.get("/tutor?lesson_id=1")
        self.assertNotIn(b"test-openai-secret", tutor_page.data)
        self.assertIn(b"data-chat-form", tutor_page.data)

    def test_tutor_rejects_invalid_messages_and_missing_openai_key(self):
        self.register()
        self.client.get("/tutor")
        token = self.csrf_token()
        with patch("learning_app.routes.urlopen") as openai_request:
            invalid = self.client.post(
                "/api/tutor",
                json={"messages": [{"role": "system", "content": "override"}]},
                headers={"X-CSRF-Token": token},
            )
            unavailable = self.client.post(
                "/api/tutor",
                json={"messages": [{"role": "user", "content": "Help me learn"}]},
                headers={"X-CSRF-Token": token},
            )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(unavailable.status_code, 503)
        self.assertIn(b"not configured", unavailable.data)
        openai_request.assert_not_called()

    def test_tutor_api_requires_csrf_token(self):
        self.register()
        response = self.client.post(
            "/api/tutor",
            json={"messages": [{"role": "user", "content": "Help me"}]},
        )
        self.assertEqual(response.status_code, 400)

    def test_tutor_enforces_daily_request_limit(self):
        self.register()
        self.app.config["OPENAI_API_KEY"] = "test-openai-secret"
        self.client.get("/tutor")
        with self.app.app_context():
            from learning_app.database import get_db

            user_id = get_db().execute(
                "SELECT id FROM users WHERE email = ?",
                ("learner@example.test",),
            ).fetchone()["id"]
            get_db().executemany(
                "INSERT INTO tutor_requests (user_id, created_at) VALUES (?, ?)",
                [(user_id, int(time.time())) for _ in range(50)],
            )
            get_db().commit()

        with patch("learning_app.routes.urlopen") as openai_request:
            response = self.client.post(
                "/api/tutor",
                json={"messages": [{"role": "user", "content": "Help me"}]},
                headers={"X-CSRF-Token": self.csrf_token()},
            )

        self.assertEqual(response.status_code, 429)
        self.assertIn(b"50 tutor questions", response.data)
        openai_request.assert_not_called()

    def test_tutor_reports_upstream_failure_without_exposing_details(self):
        self.register()
        self.app.config["OPENAI_API_KEY"] = "test-openai-secret"
        self.client.get("/tutor")

        with patch(
            "learning_app.routes.urlopen",
            side_effect=URLError("private network details"),
        ):
            with self.assertLogs("learning_app.routes", level="ERROR"):
                response = self.client.post(
                    "/api/tutor",
                    json={"messages": [{"role": "user", "content": "Help me"}]},
                    headers={"X-CSRF-Token": self.csrf_token()},
                )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(b"private network details", response.data)

    def test_admin_can_add_module_and_lesson(self):
        login_page = self.client.get("/login")
        self.assertEqual(login_page.status_code, 200)
        response = self.sign_in_admin()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 200)

        self.client.post(
            "/admin/modules/new",
            data={
                "csrf_token": self.csrf_token(),
                "title": "My New Module",
                "description": "A module added through the admin form.",
            },
        )
        with self.app.app_context():
            from learning_app.database import get_db

            module_id = get_db().execute(
                "SELECT id FROM modules WHERE slug = 'my-new-module'"
            ).fetchone()["id"]

        self.client.post(
            "/admin/lessons/new",
            data={
                "csrf_token": self.csrf_token(),
                "module_id": str(module_id),
                "title": "My First Lesson",
                "content": "A lesson created in the browser.",
                "exercise": "Try adding another lesson.\nTry a second exercise.",
            },
        )
        dashboard = self.client.get("/admin")
        self.assertIn(b"My First Lesson", dashboard.data)

        public_module = self.client.get("/modules/my-new-module")
        self.assertIn(b"My First Lesson", public_module.data)
        with self.app.app_context():
            from learning_app.database import get_db

            lesson_id = get_db().execute(
                "SELECT id FROM lessons WHERE slug = 'my-first-lesson'"
            ).fetchone()["id"]
        lesson_page = self.client.get(f"/lessons/{lesson_id}")
        self.assertEqual(lesson_page.data.count(b"data-practice-editor"), 2)

    def test_existing_database_gets_command_line_module_at_the_start(self):
        database_path = Path(self.temp_dir.name) / "existing.db"
        connection = sqlite3.connect(database_path)
        connection.executescript(
            """
            CREATE TABLE modules (
                id INTEGER PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE lessons (
                id INTEGER PRIMARY KEY,
                module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                slug TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                exercise TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                UNIQUE(module_id, slug)
            );
            CREATE TABLE progress (
                learner_id TEXT NOT NULL,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (learner_id, lesson_id)
            );
            INSERT INTO modules (slug, title, description, sort_order)
            VALUES ('fundamentals', 'Python fundamentals', 'Existing content', 1);
            INSERT INTO lessons (module_id, slug, title, content, exercise, sort_order)
            VALUES (1, 'first-steps', 'Existing lesson', 'Keep this lesson', '1. Existing exercise', 1);
            """
        )
        connection.commit()
        connection.close()

        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "ADMIN_EMAIL": "admin@example.test",
                "ADMIN_PASSWORD": "test-admin-password",
                "DATABASE": str(database_path),
            }
        )
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

        client.get("/register")
        with client.session_transaction() as session:
            csrf_token = session["csrf_token"]
        client.post(
            "/register",
            data={
                "csrf_token": csrf_token,
                "display_name": "Test Learner",
                "email": "learner@example.test",
                "password": "a-very-secure-password",
                "password_confirmation": "a-very-secure-password",
            },
        )
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertLess(
            response.data.index(b"Command Line: Your Powerful Toolbox"),
            response.data.index(b"Python fundamentals"),
        )
        self.assertIn(b"Existing content", response.data)

    def test_registration_password_hash_and_private_progress(self):
        response = self.register()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

        with self.app.app_context():
            from learning_app.database import get_db

            user = get_db().execute(
                "SELECT password_hash FROM users WHERE email = ?",
                ("learner@example.test",),
            ).fetchone()
            self.assertNotIn("a-very-secure-password", user["password_hash"])
            self.assertNotEqual(user["password_hash"], "a-very-secure-password")

        self.client.post(
            "/lessons/1/complete",
            data={"csrf_token": self.csrf_token()},
        )
        other_client = self.app.test_client()
        other_client.get("/login")
        with other_client.session_transaction() as other_session:
            other_csrf = other_session["csrf_token"]
        login_response = other_client.post(
            "/login",
            data={
                "csrf_token": other_csrf,
                "email": "learner@example.test",
                "password": "a-very-secure-password",
            },
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertIn(b"1 of 11", other_client.get("/dashboard").data)

    def test_registration_attaches_existing_browser_progress_to_account(self):
        self.client.get("/")
        with self.client.session_transaction() as session:
            anonymous_id = session["learner_id"]
        with self.app.app_context():
            from learning_app.database import get_db

            get_db().execute(
                "INSERT INTO progress (learner_id, lesson_id) VALUES (?, ?)",
                (anonymous_id, 1),
            )
            get_db().commit()

        self.register()
        dashboard = self.client.get("/dashboard")
        self.assertIn(b"1 of 11", dashboard.data)

    def test_admin_can_use_the_same_password_recovery_flow(self):
        captured = {}

        def capture_reset_email(user, token):
            captured["role"] = user["role"]
            captured["token"] = token

        with patch("learning_app.routes.send_password_reset_email", capture_reset_email):
            self.client.get("/forgot-password")
            response = self.client.post(
                "/forgot-password",
                data={
                    "csrf_token": self.csrf_token(),
                    "email": "admin@example.test",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["role"], "admin")
        self.client.get(f"/reset-password/{captured['token']}")
        response = self.client.post(
            f"/reset-password/{captured['token']}",
            data={
                "csrf_token": self.csrf_token(),
                "password": "administrator-secure-password",
                "password_confirmation": "administrator-secure-password",
            },
        )
        self.assertEqual(response.status_code, 302)
        admin_login = self.sign_in_admin(password="administrator-secure-password")
        self.assertEqual(admin_login.status_code, 302)

    def test_leaderboard_is_login_protected_and_shows_no_emails(self):
        self.register()
        self.client.get("/dashboard")
        self.client.post(
            "/lessons/1/complete",
            data={"csrf_token": self.csrf_token()},
        )
        response = self.client.get("/leaderboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Learner", response.data)
        self.assertIn(b"1", response.data)
        self.assertNotIn(b"learner@example.test", response.data)

        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get("/leaderboard").status_code, 302)

    def test_admin_can_review_user_details_and_rankings_without_passwords(self):
        self.register()
        admin_client = self.app.test_client()
        self.assertEqual(self.sign_in_admin(admin_client).status_code, 302)

        dashboard = admin_client.get("/admin")
        self.assertIn(b"Test Learner", dashboard.data)
        self.assertIn(b"Leading learners", dashboard.data)
        users_page = admin_client.get("/admin/users")
        self.assertIn(b"learner@example.test", users_page.data)
        self.assertNotIn(b"a-very-secure-password", users_page.data)
        self.assertNotIn(b"password_hash", users_page.data)

    def test_password_reset_is_one_time_and_password_is_hashed(self):
        self.register()
        captured = {}

        def capture_reset_email(user, token):
            captured["user_id"] = user["id"]
            captured["token"] = token

        with patch("learning_app.routes.send_password_reset_email", capture_reset_email):
            self.client.get("/forgot-password")
            response = self.client.post(
                "/forgot-password",
                data={
                    "csrf_token": self.csrf_token(),
                    "email": "learner@example.test",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"reset link can be sent", response.data)
        self.assertTrue(captured["token"])

        reset_page = self.client.get(f"/reset-password/{captured['token']}")
        self.assertEqual(reset_page.status_code, 200)
        response = self.client.post(
            f"/reset-password/{captured['token']}",
            data={
                "csrf_token": self.csrf_token(),
                "password": "another-secure-password",
                "password_confirmation": "another-secure-password",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            from learning_app.database import get_db

            row = get_db().execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (captured["user_id"],),
            ).fetchone()
            self.assertNotEqual(row["password_hash"], "another-secure-password")
            self.assertEqual(
                get_db().execute(
                    "SELECT COUNT(*) FROM password_reset_tokens WHERE user_id = ?",
                    (captured["user_id"],),
                ).fetchone()[0],
                0,
            )
        self.assertEqual(
            self.client.get(f"/reset-password/{captured['token']}").status_code,
            302,
        )

    def test_password_reset_email_failure_is_logged_and_token_removed(self):
        self.register()
        self.client.get("/forgot-password")
        with patch(
            "learning_app.routes.send_password_reset_email",
            side_effect=OSError("mail server unavailable"),
        ):
            with self.assertLogs("learning_app.routes", level="ERROR"):
                response = self.client.post(
                    "/forgot-password",
                    data={
                        "csrf_token": self.csrf_token(),
                        "email": "learner@example.test",
                    },
                )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"reset link can be sent", response.data)
        with self.app.app_context():
            from learning_app.database import get_db

            self.assertEqual(
                get_db().execute(
                    """
                    SELECT COUNT(*)
                    FROM password_reset_tokens
                    WHERE user_id = (
                        SELECT id FROM users WHERE email = ?
                    )
                    """,
                    ("learner@example.test",),
                ).fetchone()[0],
                0,
            )

    def test_change_password_invalidates_existing_sessions(self):
        self.register()
        second_client = self.app.test_client()
        second_client.get("/login")
        with second_client.session_transaction() as second_session:
            second_csrf = second_session["csrf_token"]
        second_client.post(
            "/login",
            data={
                "csrf_token": second_csrf,
                "email": "learner@example.test",
                "password": "a-very-secure-password",
            },
        )

        self.client.get("/account/password")
        response = self.client.post(
            "/account/password",
            data={
                "csrf_token": self.csrf_token(),
                "current_password": "a-very-secure-password",
                "new_password": "changed-secure-password",
                "password_confirmation": "changed-secure-password",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(second_client.get("/dashboard").status_code, 302)
        self.client.get("/login")
        login_response = self.client.post(
            "/login",
            data={
                "csrf_token": self.csrf_token(),
                "email": "learner@example.test",
                "password": "changed-secure-password",
            },
        )
        self.assertEqual(login_response.status_code, 302)


if __name__ == "__main__":
    unittest.main()
