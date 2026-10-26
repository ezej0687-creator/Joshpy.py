# Copilot instructions for Joshpy.py

## Project overview

This repository is a Flask-based learning platform for Python lessons. The app serves a public teaching catalog, per-user progress tracking, and an admin dashboard for creating and editing content.

The key implementation split is:

- `learning_app/__init__.py`: Flask app factory (`create_app`) and global app config. This is where the secret key, admin bootstrap values, mail settings, session behavior, CSRF enforcement, and database setup are configured.
- `learning_app/routes.py`: the main blueprint logic. It contains authentication, password reset, lesson completion, leaderboard, module/lesson pages, admin CRUD routes, and the OpenAI tutor endpoint.
- `learning_app/database.py`: SQLite schema creation, initial admin bootstrap, and seeded module/lesson content. This is the place to update schema or seed behavior when adding persistent data, including the tutor's per-account usage records.
- `learning_app/templates/` and `learning_app/static/`: Jinja templates and browser-side assets, including the Python sandbox/editor (`practice.js`) and AI tutor chat (`tutor.js`).
- `learning_app/seed_content.json`: the default course content loaded into SQLite on first run.
- `tests/test_app.py`: the repository’s unit tests and the best place to verify behavior during changes.

## Build, test, and validation commands

This project uses a local virtual environment in `.venv` and a Python unittest suite.

Set up and run the app:

```bash
cd /home/ezejo/Joshpy.py
. .venv/bin/activate
pip install -r requirements.txt

export ADMIN_EMAIL='admin@example.com'
export ADMIN_PASSWORD='choose-a-strong-admin-password'
export ADMIN_DISPLAY_NAME='Site Administrator'
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
flask --app learning_app run --debug
```

Run the full test suite:

```bash
cd /home/ezejo/Joshpy.py
. .venv/bin/activate
python -m unittest discover -s tests
```

Run a single test case (recommended for focused validation):

```bash
cd /home/ezejo/Joshpy.py
. .venv/bin/activate
python -m unittest tests.test_app.LearningAppTests.test_learning_path_and_lesson_progress
```

Useful variant when debugging a specific test method:

```bash
python -m unittest tests.test_app.LearningAppTests.test_admin_can_add_module_and_lesson
```

There is no lint configuration in this repository, so the test suite is the primary validation signal for changes.

## Architecture and data flow

The app is intentionally small and stateful rather than service-heavy:

- SQLite is the source of truth. The database file lives in `instance/learning_path.db` and is created automatically.
- Session and user state are managed with Flask `session` and `g.current_user`; route protections use decorators such as `@login_required` and `@admin_required`.
- Learner progress is split across anonymous legacy progress (`progress`) and authenticated user progress (`user_progress`). When a learner signs in, `migrate_legacy_progress()` merges the two.
- Admin bootstrap is handled by `init_db()`: if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set and no admin exists, an initial admin account is created.
- Module and lesson content are seeded from `seed_content.json`, then editable in the admin UI. Slugs are generated from human-readable titles with `make_slug()`.
- The lesson editor is browser-based; `practice.js` stores drafts locally and runs code in a sandboxed frame without sending code to the Flask server.
- The AI tutor sends validated chat messages and optional selected lesson content from the Flask server to OpenAI. Its API key is configured through `OPENAI_API_KEY`, never included in browser code, and requests are limited per account.

When making changes, assume the app is route-driven and database-backed: if you add new features, check the matching SQL schema and route handlers together, not just the page template.

## Key repository conventions

- Use the app factory pattern: create and configure the app in `learning_app/__init__.py`; do not add top-level Flask setup elsewhere.
- Keep database access in `get_db()` / `g` patterns. Most reads and writes go through `get_db()` and run in an app context.
- Preserve the project’s CSRF model. Forms submit a `csrf_token`, and `before_request` rejects invalid POST requests. New POST actions should include the token in tests and templates.
- JSON POST requests use the same CSRF protection through the `X-CSRF-Token` header. Keep API credentials in environment-backed app config and return user-safe errors for external service failures.
- Keep route behavior consistent with the app’s UX pattern: validate input, `flash()` user feedback, then `redirect()` after a successful mutation.
- Use `make_slug()` for user-created module and lesson titles to keep URL-safe identifiers consistent.
- `parse_exercises()` normalizes lesson exercises by stripping numbering/bullets and storing one exercise per line. If content editing affects the lesson authoring flow, keep that behavior consistent.
- For admin-only or authenticated flows, prefer the existing decorators and redirection patterns rather than custom access checks.
- The project stores a persistent local SQLite file for regular development. Unit tests isolate this by passing a temporary `DATABASE` path via `create_app(...)`.

## Content and change guidance

When updating the learning content or app behavior:

- Keep module/lesson data compatible with the seeded schema in `database.py`.
- Prefer updating `learning_app/seed_content.json` if the change is part of the starter course content.
- Verify web-facing behavior with the Flask test client and the existing unittest cases rather than ad hoc scripts.
- Keep changes focused on the app’s route + database + template flow; this project is small enough that architecture is usually understood by reading those pieces together.
