# Python Learning Web App

A small, extendable Flask app for learning Python. Learners can browse modules,
open lessons, and track completed lessons. An administrator can add and edit
modules and lessons through the website.

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set an admin password and a secret key before starting:

```bash
export ADMIN_PASSWORD='choose-a-local-admin-password'
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
flask --app learning_app run --debug
```

On Windows PowerShell, set the variables with `$env:ADMIN_PASSWORD = "..."` and
`$env:SECRET_KEY = "..."` before running the Flask command.

Open <http://127.0.0.1:5000>. The administrator sign-in is at
<http://127.0.0.1:5000/admin/login>.

The SQLite database is created at `instance/learning_path.db` and seeded with
the starter learning path on first run. It persists your content between runs.
Progress is saved per browser using a signed cookie, so it does not require
learner accounts. Changing browsers or clearing cookies starts a separate
progress record.

## Add learning content

Sign in as administrator, then choose **Manage content**. Create modules first,
then add lessons to them. You can edit existing module and lesson titles,
descriptions, and lesson text. Enter one exercise per line; each exercise gets
its own Python editor. Lesson content is plain text; line breaks are preserved.
The browser editor uses Python syntax highlighting, saves drafts in the current
browser, runs Python in a sandboxed browser frame, and can download a `.py`
file. An optional program-input box supplies lines to Python's `input()`. The
code is not sent to or executed on the Flask server. The first run downloads
the Pyodide runtime from jsDelivr and CodeMirror is loaded from cdnjs; an
internet connection is needed for the full editor and Python runner.

The first module, **Command Line: Your Powerful Toolbox**, introduces safe
terminal basics and how to run downloaded Python files from your own terminal.
The web editor does not execute shell commands.

The app code lives in `learning_app/`:

- `routes.py` contains learner pages and content-management routes.
- `database.py` defines and seeds the SQLite tables.
- `templates/` contains the page layouts.
- `static/style.css` contains the presentation.
- `static/practice.js` stores exercise drafts and connects editors to the isolated browser runtime.

The original runnable Python examples remain in `lessons/`; they are useful
reference material while expanding the web app's starter content.

## Security note

The admin pages require `ADMIN_PASSWORD`. Keep `SECRET_KEY` private and stable
when running the app so sessions remain valid. The Flask debug server is for
local development only; do not expose it as a production server.
