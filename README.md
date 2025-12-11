# Live Quiz Platform

A real-time multiplayer quiz platform built with Flask and Socket.IO.

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/MWong08/live-quiz-platform.git
cd live-quiz-platform
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
python -m pip install -r requirements.txt
```

### 2. Run Locally

```bash
python app.py
```

Visit `http://localhost:5000`

### 3. Share with ngrok (optional)

```bash
ngrok http 5000
```

Share the public URL with others for demos.

## Features

- Create custom quizzes with multiple choice questions
- Real-time multiplayer games with live leaderboards
- Admin dashboard with secure login
- Export/import quizzes as JSON or CSV
- Works on desktop and mobile

## Usage

1. **Register**: Create admin account at `/admin/login`
2. **Create Quiz**: Add questions and answers
3. **Host Game**: Start a game and share the code
4. **Players Join**: Visit `/game/join` and enter the code
5. **Play**: Answer questions and watch the leaderboard update

## Deployment

**Option 1: Render (Cloud)**
- Push to GitHub
- Connect to Render.com
- Set `DATABASE_URL` and `SECRET_KEY` environment variables
- Deploy with PostgreSQL database

**Option 2: ngrok (Local Demo)**
- Run `ngrok http 5000` while app is running
- Share the public URL with others

## Tech Stack

- Backend: Flask, Socket.IO
- Database: PostgreSQL (production) / SQLite (local)
- Frontend: HTML, CSS, JavaScript
- Server: Gunicorn with Eventlet
