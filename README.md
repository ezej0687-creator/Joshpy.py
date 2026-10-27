# 🐍 Joshtech

**Joshtech** is a modern, interactive Python learning platform. It combines a full curriculum with an AI-powered tutor and a browser-based Python execution environment to help beginners become engineers.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-black?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- **📚 Structured Curriculum:** 10+ modules covering foundational Python up to Engineer-tier concepts (like Debugging).
- **🤖 AI Tutor:** A built-in AI assistant (powered by Groq) that knows the curriculum context and helps you unblock without giving away the answer.
- **💻 In-Browser IDE:** Write and execute real Python code right in the lesson page using Pyodide (WebAssembly). No local setup required.
- **✅ Auto-Graded Exercises:** LeetCode-style challenges that unlock sequentially as you pass hidden test suites.
- **🏆 Gamification:** Earn progress badges, watch the confetti fly when you complete a lesson, and climb the leaderboard.
- **🔐 Secure Auth:** Full user registration, login, password toggles, and CSRF protection.

## 🚀 Quick Start

### 1. Clone the repository
git clone https://github.com/ezej0687-creator/Joshpy.py.git
cd Joshpy.py

### 2. Set up the virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

### 3. Configure environment variables
Copy the example file and add your keys:
cp .env.example .env
Open `.env` and fill in:
- `SECRET_KEY`: A random string (generate one with `python -c "import secrets; print(secrets.token_hex(32))"`)
- `GROQ_API_KEY`: Get a free one at console.groq.com

### 4. Run the app
flask --app learning_app run --debug

Visit **http://127.0.0.1:5000** in your browser.

## 🧠 Tech Stack

- **Backend:** Flask, SQLite, Werkzeug (Security)
- **Frontend:** Jinja2, Vanilla CSS (Custom Design System), Vanilla JS
- **Code Execution:** Pyodide (WebAssembly)
- **AI Provider:** Groq (Llama 3 / GPT-OSS)

## 📁 Project Structure

Joshpy.py/
├── learning_app/          # Main Flask application
│   ├── database.py        # SQLite schema & seeding
│   ├── routes.py          # Application endpoints
│   ├── challenges.py      # Auto-graded exercise logic
│   ├── static/            # CSS, JS, and assets
│   └── templates/         # Jinja2 HTML templates
├── lessons/               # Course content (content & tests)
│   └── 09_debugging/      # Lesson JSON & capstone projects
├── instance/              # Local SQLite database (git-ignored)
└── run.py                 # App entry point

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
