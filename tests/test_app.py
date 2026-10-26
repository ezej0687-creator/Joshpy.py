import tempfile
import unittest
from pathlib import Path

from learning_app import create_app


class LearningAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "ADMIN_PASSWORD": "test-admin-password",
                "DATABASE": str(database_path),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def test_learning_path_and_lesson_progress(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Fundamentals", response.data)

        lesson_response = self.client.get("/lessons/1")
        self.assertEqual(lesson_response.status_code, 200)
        response = self.client.post(
            "/lessons/1/complete",
            data={"csrf_token": self.csrf_token()},
        )
        self.assertEqual(response.status_code, 302)

        completed_response = self.client.get("/lessons/1")
        self.assertIn(b"Completed", completed_response.data)

    def test_completion_requires_csrf_token(self):
        response = self.client.post("/lessons/1/complete")
        self.assertEqual(response.status_code, 400)

    def test_admin_can_add_module_and_lesson(self):
        login_page = self.client.get("/admin/login")
        self.assertEqual(login_page.status_code, 200)
        response = self.client.post(
            "/admin/login",
            data={
                "csrf_token": self.csrf_token(),
                "password": "test-admin-password",
            },
        )
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
                "exercise": "Try adding another lesson.",
            },
        )
        dashboard = self.client.get("/admin")
        self.assertIn(b"My First Lesson", dashboard.data)

        public_module = self.client.get("/modules/my-new-module")
        self.assertIn(b"My First Lesson", public_module.data)


if __name__ == "__main__":
    unittest.main()
