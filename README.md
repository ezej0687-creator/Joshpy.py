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

Set the first admin's email and password plus a stable secret key before
starting. The first administrator account is created from these settings if the
database does not already contain an administrator:

```bash
export ADMIN_EMAIL='admin@example.com'
export ADMIN_PASSWORD='choose-a-strong-admin-password'
export ADMIN_DISPLAY_NAME='Site Administrator'
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
flask --app learning_app run --debug
```

On Windows PowerShell, set the variables with `$env:ADMIN_EMAIL = "..."`,
`$env:ADMIN_PASSWORD = "..."`, and `$env:SECRET_KEY = "..."` before running the
Flask command.

Open <http://127.0.0.1:5000>. The administrator sign-in is at
<http://127.0.0.1:5000/admin/login>.

The admin sign-in page is <http://127.0.0.1:5000/login>; `/admin/login`
redirects there for compatibility.

The SQLite database is created at `instance/learning_path.db` and seeded with
the starter learning path on first run. It persists your content and registered
accounts between runs. Existing anonymous lesson progress is retained and
attached to an account when that browser registers or signs in.

## Accounts and learner progress

Learners can register with a display name, email, and password. Passwords are
at least 12 characters and are stored as Werkzeug password hashes; neither
admins nor the database store readable passwords. Learners get a personal
dashboard, can change their password, and can see the leaderboard. The
leaderboard is visible only after sign-in and shows display names and
completed-lesson counts, never email addresses. Admins can see registered
users' names, email addresses, join dates, and progress at
**Manage content → Learners**.

## AI tutor

Signed-in learners can use **AI tutor** in the navigation for course-wide Python
guidance, or open the tutor from a lesson to include that lesson's material and
exercises as context. The tutor uses the OpenAI API from the Flask server; the
API key is never sent to the browser. Conversations remain in the current page
only and are not saved by this app. Messages and selected lesson text are sent
to OpenAI to generate replies. Avoid entering personal or sensitive information,
and review OpenAI's current data and usage policies before enabling the feature.
API usage may incur charges on the account that owns the key. Each account is
limited to 50 tutor requests in a rolling 24-hour window.

Set an OpenAI API key before starting the app:

```bash
export OPENAI_API_KEY='your-openai-api-key'
```

In Windows PowerShell, use `$env:OPENAI_API_KEY = "your-openai-api-key"`.

The tutor uses `gpt-4o-mini` by default. To choose another model supported by
the Chat Completions API, set `OPENAI_MODEL`. Restart the Flask app after
changing either setting. Without an API key the app continues to run, but the
tutor UI displays setup instructions and chat requests are unavailable.

Password-reset links are single-use and expire after 30 minutes. To enable
forgot-password for learners and administrators, configure an SMTP sender and
a canonical public URL before starting the app:

```bash
export MAIL_SERVER='smtp.example.com'
export MAIL_PORT='587'
export MAIL_USERNAME='smtp-account'
export MAIL_PASSWORD='smtp-password'
export MAIL_USE_TLS='true'
export MAIL_DEFAULT_SENDER='Python Learning <no-reply@example.com>'
export PUBLIC_BASE_URL='https://learning.example.com'
```

`MAIL_USERNAME` and `MAIL_PASSWORD` can be omitted if the SMTP server does not
require authentication. Keep mail credentials and `SECRET_KEY` out of source
control. If SMTP is not configured, the app explains that account recovery is
unavailable instead of pretending a reset email was sent.

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

Use strong admin and SMTP credentials. Keep `SECRET_KEY` private and stable
when running the app so sessions remain valid. Set `COOKIE_SECURE=true` when
serving the site over HTTPS. The Flask debug server is for local development
only; use a production WSGI server and HTTPS before exposing the app publicly.
