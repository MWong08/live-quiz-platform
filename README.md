# Live Quiz Platform

A real-time multiplayer quiz platform built with Flask and Socket.IO. Host interactive quizzes, track scores in real-time, and engage audiences with live leaderboards.

## Features

- 🎯 **Create & Manage Quizzes** - Build custom quizzes with multiple choice questions
- 👥 **Real-time Multiplayer** - Players join live games and compete simultaneously
- 📊 **Live Leaderboards** - Watch scores update in real-time during gameplay
- 🔐 **Admin Dashboard** - Secure login for quiz creators
- 📱 **Responsive Design** - Works on desktop and mobile devices
- 💾 **Export/Import** - Back up quizzes in JSON or CSV format
- 🗄️ **PostgreSQL Database** - Scalable data storage for production

## Prerequisites

- Python 3.12+
- PostgreSQL (for production) or SQLite (for local development)
- pip (Python package manager)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/MWong08/live-quiz-platform.git
cd live-quiz-platform
```

### 2. Create Virtual Environment

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or
source venv/bin/activate  # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Local development (default - uses SQLite)
DATABASE_URL=sqlite:///database.db

# Or use PostgreSQL for production
# DATABASE_URL=postgresql://username:password@localhost:5432/troffee_db

# Flask secret key for sessions
SECRET_KEY=your-secret-key-here
```

### 5. Run the Application

```bash
python app.py
```

The app will start at `http://localhost:5000`

## Usage

### Creating a Quiz

1. Go to `http://localhost:5000/admin/login`
2. Register a new admin account or log in
3. Click "Create Quiz" and add questions with multiple choice answers
4. Mark the correct answers

### Hosting a Game

1. From the admin dashboard, select a quiz
2. Click "Host Game" to start a new game session
3. Share the game code with players
4. Players visit `http://localhost:5000/game/join` and enter the code and their nickname
5. Click "Start Game" to begin
6. Questions display for all players simultaneously
7. Watch the live leaderboard update as players submit answers

### Playing a Game

1. Go to `http://localhost:5000/game/join`
2. Enter the game code and your nickname
3. Wait for the game to start
4. Answer questions as they appear
5. Check the leaderboard at the end

## Deployment

### Deploy to Render

1. Push your code to GitHub
2. Create a Render account at https://render.com
3. Connect your GitHub repository
4. Create a new Web Service
5. Set environment variables:
   - `DATABASE_URL` - PostgreSQL connection string (create a free PostgreSQL database in Render)
   - `SECRET_KEY` - Secure random string
6. Deploy!

### Using ngrok for Local Demos

To demo your local app publicly without deploying:

1. Install ngrok: https://ngrok.com/download
2. Authenticate: `ngrok config add-authtoken YOUR_TOKEN`
3. Start your Flask app: `python app.py`
4. In another terminal, start ngrok: `ngrok http 5000`
5. Share the public URL with others (e.g., `https://xxxxx.ngrok-free.dev`)

The ngrok URL will expire when you restart, but it's perfect for live demos without deployment costs.

## Project Structure

```
live-quiz-platform/
├── app.py                 # Flask application and Socket.IO events
├── models.py              # SQLAlchemy database models
├── requirements.txt       # Python dependencies
├── Procfile              # Production deployment configuration
├── runtime.txt           # Python version specification
├── .env.example          # Environment variables template
└── templates/
    ├── index.html        # Home page
    ├── admin_login.html  # Admin login/registration
    ├── admin_dashboard.html  # Quiz management
    ├── create_quiz.html  # Quiz creation form
    ├── host_game.html    # Game host view (admin side)
    ├── join_game.html    # Player join page
    └── play_game.html    # Game play interface
```

## Database Models

- **Admin** - User accounts for quiz creators
- **Quiz** - Quiz content (title, description, questions)
- **Question** - Individual questions within a quiz
- **Answer** - Multiple choice answers for questions
- **GameSession** - Active or completed game instances
- **Participant** - Players in a game session
- **ParticipantAnswer** - Individual player responses

## API Endpoints

### Authentication
- `POST /api/register` - Create new admin account
- `POST /api/login` - Admin login

### Quiz Management
- `POST /api/quiz` - Create quiz
- `GET /api/quiz/<id>` - Get quiz details
- `PUT /api/quiz/<id>` - Update quiz
- `DELETE /api/quiz/<id>` - Delete quiz
- `POST /api/quiz/<id>/question` - Add question
- `GET /api/admin/<id>/quizzes` - Get all quizzes for admin
- `GET /api/admin/<id>/stats` - Get admin statistics

### Game
- `POST /api/game/start` - Start new game session
- `GET /api/admin/<id>/stats` - Get game statistics

### Export/Import
- `GET /api/quiz/<id>/export?format=json|csv` - Export quiz
- `GET /api/admin/<id>/quizzes/export-all?format=json|csv` - Export all quizzes
- `POST /api/admin/<id>/quizzes/import` - Import quiz from file

## Socket.IO Events

Real-time events for multiplayer gameplay:

- `join_game` - Player joins a game
- `start_game` - Host starts the game
- `show_question` - Display question to all players
- `submit_answer` - Player submits answer
- `get_leaderboard` - Request leaderboard data
- `broadcast_leaderboard` - Send leaderboard to all players
- `end_game` - End the game session

## Troubleshooting

### 502 Bad Gateway (ngrok)
- Ensure Flask app is running on port 5000
- Check that venv is activated
- Run `python app.py` in the Python terminal

### Module not found errors
- Activate venv: `.\venv\Scripts\Activate.ps1`
- Install dependencies: `pip install -r requirements.txt`

### Database errors
- Delete `instance/database.db` to reset local database
- Ensure `DATABASE_URL` environment variable is set correctly

### Socket.IO connection issues
- Clear browser cache
- Check that Flask app is running
- Verify ngrok/Render is properly forwarding connections

## Technologies Used

- **Backend**: Flask, Flask-SQLAlchemy, Flask-SocketIO
- **Real-time Communication**: Socket.IO, Eventlet
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Render, ngrok
- **Server**: Gunicorn with Eventlet workers

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub: https://github.com/MWong08/live-quiz-platform/issues
