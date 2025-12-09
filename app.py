from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, Admin, Quiz, Question, Answer, GameSession, Participant, ParticipantAnswer
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from datetime import datetime, timezone
import json
import csv
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
# Handle postgres:// → postgresql://
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create database tables
with app.app_context():
    db.create_all()
    print("Database tables created!")

# Helper function to generate game code
def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/create-quiz')
def create_quiz_page():
    return render_template('create_quiz.html')

@app.route('/game/join')
def join_game_page():
    return render_template('join_game.html')

@app.route('/game/play/<game_code>')
def play_game(game_code):
    return render_template('play_game.html', game_code=game_code)

@app.route('/admin/host/<game_code>')
def host_game(game_code):
    return render_template('host_game.html', game_code=game_code)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data['email'].lower()
    
    # Check if email already exists
    if Admin.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Check if username already exists
    if Admin.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    # Create new admin
    hashed_password = generate_password_hash(data['password'])
    new_admin = Admin(
        username=data['username'],
        email=email,
        password_hash=hashed_password
    )
    
    try:
        db.session.add(new_admin)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed. Please try again.'}), 500
    
    return jsonify({'message': 'Admin registered successfully', 'admin_id': new_admin.admin_id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data['email'].lower()
    admin = Admin.query.filter_by(email=email).first()
    
    if admin and check_password_hash(admin.password_hash, data['password']):
        return jsonify({
            'message': 'Login successful',
            'admin_id': admin.admin_id,
            'username': admin.username,
            'email': admin.email
        }), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/quiz', methods=['POST'])
def create_quiz():
    data = request.json
    
    new_quiz = Quiz(
        admin_id=data['admin_id'],
        title=data['title'],
        description=data.get('description', '')
    )
    
    db.session.add(new_quiz)
    db.session.commit()
    
    return jsonify({
        'message': 'Quiz created successfully',
        'quiz_id': new_quiz.quiz_id
    }), 201

@app.route('/api/quiz/<int:quiz_id>/question', methods=['POST'])
def add_question(quiz_id):
    data = request.json
    
    # Get the quiz to verify ownership
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Check if the quiz belongs to the requesting admin
    admin_id = data.get('admin_id')
    if not admin_id or int(admin_id) != quiz.admin_id:
        return jsonify({'error': 'Unauthorized: You do not have permission to edit this quiz'}), 403
    
    new_question = Question(
        quiz_id=quiz_id,
        question_text=data['question_text'],
        question_order=data['question_order'],
        time_limit=data.get('time_limit', 30),
        points=data.get('points', 100)
    )
    
    db.session.add(new_question)
    db.session.commit()
    
    # Add answers
    for answer_data in data['answers']:
        new_answer = Answer(
            question_id=new_question.question_id,
            answer_text=answer_data['answer_text'],
            is_correct=answer_data['is_correct'],
            answer_order=answer_data['answer_order']
        )
        db.session.add(new_answer)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Question added successfully',
        'question_id': new_question.question_id
    }), 201

@app.route('/api/quiz/<int:quiz_id>/questions', methods=['DELETE'])
def delete_all_questions(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Check if the quiz belongs to the requesting admin
    admin_id = request.args.get('admin_id', type=int)
    if not admin_id or int(admin_id) != quiz.admin_id:
        return jsonify({'error': 'Unauthorized: You do not have permission to edit this quiz'}), 403
    
    try:
        # Get all questions for this quiz
        questions = Question.query.filter_by(quiz_id=quiz_id).all()
        
        # Delete in correct order: participant_answers -> answers -> questions
        for question in questions:
            # Delete participant answers first (they reference answers)
            participant_answers = ParticipantAnswer.query.filter_by(question_id=question.question_id).all()
            for pa in participant_answers:
                db.session.delete(pa)
            
            # Delete answers
            answers = Answer.query.filter_by(question_id=question.question_id).all()
            for answer in answers:
                db.session.delete(answer)
        
        # Flush to ensure all dependent records are deleted
        db.session.flush()
        
        # Delete all questions
        for question in questions:
            db.session.delete(question)
        
        # Commit all deletions
        db.session.commit()
        return jsonify({'message': 'All questions deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting questions: {str(e)}")
        return jsonify({'error': 'Failed to delete questions'}), 500

@app.route('/api/quiz/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Check if the quiz belongs to the requesting admin
    admin_id = request.args.get('admin_id', type=int)
    if not admin_id or quiz.admin_id != admin_id:
        return jsonify({'error': 'Unauthorized: You do not have permission to access this quiz'}), 403
    
    questions_data = []
    for question in quiz.questions:
        answers_data = []
        for answer in question.answers:
            answers_data.append({
                'answer_id': answer.answer_id,
                'answer_text': answer.answer_text,
                'is_correct': answer.is_correct,
                'answer_order': answer.answer_order
            })
        
        questions_data.append({
            'question_id': question.question_id,
            'question_text': question.question_text,
            'question_order': question.question_order,
            'time_limit': question.time_limit,
            'points': question.points,
            'answers': sorted(answers_data, key=lambda x: x['answer_order'])
        })
    
    return jsonify({
        'quiz_id': quiz.quiz_id,
        'title': quiz.title,
        'description': quiz.description,
        'questions': sorted(questions_data, key=lambda x: x['question_order'])
    }), 200

@app.route('/api/admin/<int:admin_id>/quizzes', methods=['GET'])
def get_admin_quizzes(admin_id):
    quizzes = Quiz.query.filter_by(admin_id=admin_id).all()
    
    quiz_list = []
    for quiz in quizzes:
        quiz_list.append({
            'quiz_id': quiz.quiz_id,
            'title': quiz.title,
            'description': quiz.description,
            'created_at': quiz.created_at.strftime('%Y-%m-%d'),
            'question_count': len(quiz.questions)
        })
    
    return jsonify(quiz_list), 200

@app.route('/api/admin/<int:admin_id>/stats', methods=['GET'])
def get_admin_stats(admin_id):
    # Verify admin exists
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Get total quizzes
    total_quizzes = len(admin.quizzes)
    
    # Get total questions
    total_questions = 0
    for quiz in admin.quizzes:
        total_questions += len(quiz.questions)
    
    # Get total games hosted
    total_games = len(admin.game_sessions)
    
    # Get total participants across all games
    total_participants = 0
    for game in admin.game_sessions:
        total_participants += len(game.participants)
    
    # Get recent activity
    recent_activity = []
    for quiz in admin.quizzes:
        recent_activity.append({
            'title': quiz.title,
            'type': 'Quiz Created',
            'date': quiz.created_at.strftime('%Y-%m-%d %H:%M'),
            'timestamp': quiz.created_at
        })
        # Add game sessions for this quiz
        for game in quiz.game_sessions:
            if game.started_at:
                recent_activity.append({
                    'title': quiz.title,
                    'type': 'Game Hosted',
                    'date': game.started_at.strftime('%Y-%m-%d %H:%M'),
                    'timestamp': game.started_at
                })
    
    # Sort by timestamp descending, then remove timestamp field
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    for item in recent_activity:
        del item['timestamp']
    
    return jsonify({
        'total_quizzes': total_quizzes,
        'total_questions': total_questions,
        'total_games': total_games,
        'total_participants': total_participants,
        'recent_activity': recent_activity[:10]  # Limit to 10 items
    }), 200

@app.route('/api/quiz/<int:quiz_id>', methods=['PUT'])
def update_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    data = request.json
    admin_id = data.get('admin_id')
    
    # Check if the quiz belongs to the requesting admin
    if not admin_id or int(admin_id) != quiz.admin_id:
        return jsonify({'error': 'Unauthorized: You do not have permission to edit this quiz'}), 403
    
    quiz.title = data.get('title', quiz.title)
    quiz.description = data.get('description', quiz.description)
    quiz.updated_at = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Quiz updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update quiz'}), 500

@app.route('/api/quiz/<int:quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Check if the quiz belongs to the requesting admin
    # Try to get admin_id from JSON body first, then from query parameters
    data = request.get_json() or {}
    admin_id = data.get('admin_id') or request.args.get('admin_id', type=int)
    
    if not admin_id or quiz.admin_id != admin_id:
        return jsonify({'error': 'Unauthorized: You do not have permission to delete this quiz'}), 403
    
    try:
        db.session.delete(quiz)
        db.session.commit()
        return jsonify({'message': 'Quiz deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete quiz'}), 500

@app.route('/api/admin/<int:admin_id>/settings', methods=['PUT'])
def update_admin_settings(admin_id):
    data = request.json
    admin = Admin.query.get(admin_id)
    
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Verify current password if trying to change password
    if data.get('new_password'):
        current_password = data.get('current_password')
        if not current_password or not check_password_hash(admin.password_hash, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        admin.password_hash = generate_password_hash(data['new_password'])
    
    try:
        db.session.commit()
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update settings'}), 500

@app.route('/api/game/start', methods=['POST'])
def start_game():
    data = request.json
    
    game_code = generate_game_code()
    
    new_session = GameSession(
        quiz_id=data['quiz_id'],
        admin_id=data['admin_id'],
        game_code=game_code,
        status='waiting'
    )
    
    db.session.add(new_session)
    db.session.commit()
    
    return jsonify({
        'message': 'Game session created',
        'game_code': game_code,
        'game_session_id': new_session.game_session_id
    }), 201

# SocketIO events for real-time communication
@socketio.on('join_game')
def handle_join_game(data):
    game_code = data['game_code']
    nickname = data['nickname']
    print(f"[DEBUG] Player {nickname} attempting to join game: {game_code}")
    
    # Find game session
    session = GameSession.query.filter_by(game_code=game_code).first()
    
    if not session:
        print(f"[DEBUG] Game session not found for code: {game_code}")
        emit('error', {'message': 'Game not found'})
        return
    
    print(f"[DEBUG] Game session found. Creating participant...")
    # Create participant
    participant = Participant(
        game_session_id=session.game_session_id,
        nickname=nickname
    )
    
    db.session.add(participant)
    db.session.commit()
    
    # Join the game code room so player receives game_started event
    join_room(game_code)
    print(f"[DEBUG] Participant {nickname} joined room: {game_code}")
    
    # Notify player they joined
    emit('joined', {
        'participant_id': participant.participant_id,
        'nickname': nickname
    })
    
    # Notify host that someone joined
    emit('participant_joined', {
        'participant_id': participant.participant_id,
        'nickname': nickname
    }, room=f'host_{game_code}')
    print(f"[DEBUG] Notified host about new participant in game: {game_code}")

@socketio.on('join_room')
def handle_join_room(data):
    """Join a socket room to receive broadcasts (used by play_game.html)"""
    game_code = data['game_code']
    print(f"[DEBUG] Socket joining room for game code: {game_code}")
    join_room(game_code)
    print(f"[DEBUG] Socket joined room: {game_code}")

@socketio.on('join_host_room')
def handle_join_host_room(data):
    game_code = data['game_code']
    join_room(f'host_{game_code}')
    
    # Send quiz data to host
    session = GameSession.query.filter_by(game_code=game_code).first()
    if session:
        quiz = Quiz.query.get(session.quiz_id)
        questions_data = []
        
        for question in quiz.questions:
            answers_data = []
            for answer in question.answers:
                answers_data.append({
                    'answer_id': answer.answer_id,
                    'answer_text': answer.answer_text,
                    'is_correct': answer.is_correct
                })
            
            questions_data.append({
                'question_id': question.question_id,
                'question_text': question.question_text,
                'time_limit': question.time_limit,
                'points': question.points,
                'answers': answers_data
            })
        
        emit('quiz_data', {'questions': questions_data})

@socketio.on('start_game')
def handle_start_game(data):
    game_code = data['game_code']
    print(f"[DEBUG] Admin starting game with code: {game_code}")
    
    # Update game session status
    session = GameSession.query.filter_by(game_code=game_code).first()
    if session:
        print(f"[DEBUG] Game session found: {session.game_code}, status: {session.status}")
        session.status = 'active'
        session.started_at = datetime.now(timezone.utc)
        db.session.commit()
        print(f"[DEBUG] Emitting game_started to room: {game_code}")
    else:
        print(f"[DEBUG] Game session NOT found for code: {game_code}")
    
    emit('game_started', {}, room=game_code)
    print(f"[DEBUG] game_started emitted to room: {game_code}")

@socketio.on('show_question')
def handle_show_question(data):
    game_code = data['game_code']
    question = data['question']
    print(f"[DEBUG] Broadcasting show_question to room {game_code}: Question {question.get('question_number')}")
    
    emit('show_question', question, room=game_code)
    print(f"[DEBUG] show_question broadcast complete")

@socketio.on('submit_answer')
def handle_submit_answer(data):
    # Handle both single answer (backwards compatibility) and multiple answers
    answer_ids = data.get('answer_ids', [data['answer_id']] if 'answer_id' in data else [])
    
    # Create participant answers for each selected answer
    for answer_id in answer_ids:
        participant_answer = ParticipantAnswer(
            participant_id=data['participant_id'],
            question_id=data['question_id'],
            answer_id=answer_id,
            time_taken=data['time_taken'],
            points_earned=data['points_earned']
        )
        db.session.add(participant_answer)
    
    # Update participant total score
    participant = Participant.query.get(data['participant_id'])
    participant.total_score += data['points_earned']
    
    db.session.commit()
    
    # Check if all answers are correct
    question = Question.query.get(data['question_id'])
    correct_answers = Answer.query.filter_by(question_id=data['question_id'], is_correct=True).all()
    correct_answer_ids = set(a.answer_id for a in correct_answers)
    selected_answer_ids = set(answer_ids)
    
    # Answers are correct if the selected set exactly matches the correct set
    is_correct = selected_answer_ids == correct_answer_ids
    
    # Notify host
    game_session = GameSession.query.join(Participant).filter(
        Participant.participant_id == data['participant_id']
    ).first()
    
    if game_session:
        emit('answer_submitted', {
            'participant_id': data['participant_id'],
            'correct': is_correct,
            'time_taken': data['time_taken']
        }, room=f'host_{game_session.game_code}')
    
    emit('answer_submitted', {'success': True})

@socketio.on('get_leaderboard')
def handle_get_leaderboard(data):
    game_code = data['game_code']
    
    session = GameSession.query.filter_by(game_code=game_code).first()
    if session:
        participants = Participant.query.filter_by(
            game_session_id=session.game_session_id
        ).order_by(Participant.total_score.desc()).all()
        
        leaderboard = []
        for p in participants:
            leaderboard.append({
                'participant_id': p.participant_id,
                'nickname': p.nickname,
                'total_score': p.total_score
            })
        
        emit('leaderboard_data', {'leaderboard': leaderboard})

@socketio.on('broadcast_leaderboard')
def handle_broadcast_leaderboard(data):
    game_code = data['game_code']
    leaderboard = data['leaderboard']
    
    emit('show_leaderboard', {'leaderboard': leaderboard}, room=game_code)

@socketio.on('end_game')
def handle_end_game(data):
    game_code = data['game_code']
    
    # Update game session
    session = GameSession.query.filter_by(game_code=game_code).first()
    if session:
        session.status = 'completed'
        session.ended_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Get final leaderboard
        participants = Participant.query.filter_by(
            game_session_id=session.game_session_id
        ).order_by(Participant.total_score.desc()).all()
        
        leaderboard = []
        for p in participants:
            leaderboard.append({
                'participant_id': p.participant_id,
                'nickname': p.nickname,
                'total_score': p.total_score
            })
        
        emit('game_ended', {'leaderboard': leaderboard}, room=game_code)

# Export/Import Endpoints
@app.route('/api/quiz/<int:quiz_id>/export', methods=['GET'])
def export_quiz(quiz_id):
    """Export a single quiz as JSON or CSV"""
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Check if the quiz belongs to the requesting admin
    admin_id = request.args.get('admin_id', type=int)
    if not admin_id or quiz.admin_id != admin_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    export_format = request.args.get('format', 'json').lower()
    
    # Build quiz data
    quiz_data = {
        'quiz_id': quiz.quiz_id,
        'title': quiz.title,
        'description': quiz.description,
        'questions': []
    }
    
    for question in sorted(quiz.questions, key=lambda q: q.question_order):
        question_data = {
            'question_text': question.question_text,
            'question_order': question.question_order,
            'time_limit': question.time_limit,
            'points': question.points,
            'answers': []
        }
        
        for answer in sorted(question.answers, key=lambda a: a.answer_order):
            question_data['answers'].append({
                'answer_text': answer.answer_text,
                'is_correct': answer.is_correct,
                'answer_order': answer.answer_order
            })
        
        quiz_data['questions'].append(question_data)
    
    if export_format == 'json':
        # Export as JSON
        json_data = json.dumps(quiz_data, indent=2)
        return send_file(
            io.BytesIO(json_data.encode()),
            mimetype='application/json',
            as_attachment=True,
            download_name=f'{quiz.title.replace(" ", "_")}.json'
        )
    
    elif export_format == 'csv':
        # Export as CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header with quiz info
        writer.writerow(['Quiz Title', quiz.title])
        writer.writerow(['Description', quiz.description])
        writer.writerow([])  # Blank row
        
        # Write column headers
        writer.writerow(['Question Order', 'Question Text', 'Time Limit (sec)', 'Points', 'Answer Text', 'Is Correct', 'Answer Order'])
        
        # Write data rows
        for question in sorted(quiz.questions, key=lambda q: q.question_order):
            for i, answer in enumerate(sorted(question.answers, key=lambda a: a.answer_order)):
                if i == 0:
                    writer.writerow([
                        question.question_order,
                        question.question_text,
                        question.time_limit,
                        question.points,
                        answer.answer_text,
                        'Yes' if answer.is_correct else 'No',
                        answer.answer_order
                    ])
                else:
                    writer.writerow([
                        '',
                        '',
                        '',
                        '',
                        answer.answer_text,
                        'Yes' if answer.is_correct else 'No',
                        answer.answer_order
                    ])
        
        csv_data = output.getvalue()
        return send_file(
            io.BytesIO(csv_data.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{quiz.title.replace(" ", "_")}.csv'
        )
    
    return jsonify({'error': 'Invalid format. Use "json" or "csv"'}), 400

@app.route('/api/admin/<int:admin_id>/quizzes/export-all', methods=['GET'])
def export_all_quizzes(admin_id):
    """Export all quizzes for an admin as JSON or CSV"""
    admin = Admin.query.get(admin_id)
    
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Verify the requesting user is the admin
    request_admin_id = request.args.get('admin_id', type=int)
    if not request_admin_id or request_admin_id != admin_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    export_format = request.args.get('format', 'json').lower()
    
    quizzes_data = []
    for quiz in admin.quizzes:
        quiz_data = {
            'quiz_id': quiz.quiz_id,
            'title': quiz.title,
            'description': quiz.description,
            'questions': []
        }
        
        for question in sorted(quiz.questions, key=lambda q: q.question_order):
            question_data = {
                'question_text': question.question_text,
                'question_order': question.question_order,
                'time_limit': question.time_limit,
                'points': question.points,
                'answers': []
            }
            
            for answer in sorted(question.answers, key=lambda a: a.answer_order):
                question_data['answers'].append({
                    'answer_text': answer.answer_text,
                    'is_correct': answer.is_correct,
                    'answer_order': answer.answer_order
                })
            
            quiz_data['questions'].append(question_data)
        
        quizzes_data.append(quiz_data)
    
    if export_format == 'json':
        # Export as JSON
        json_data = json.dumps(quizzes_data, indent=2)
        return send_file(
            io.BytesIO(json_data.encode()),
            mimetype='application/json',
            as_attachment=True,
            download_name=f'quizzes_export_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.json'
        )
    
    elif export_format == 'csv':
        # Export as CSV (combined)
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Quiz Title', 'Description', 'Question Order', 'Question Text', 'Time Limit (sec)', 'Points', 'Answer Text', 'Is Correct', 'Answer Order'])
        
        for quiz in admin.quizzes:
            for question in sorted(quiz.questions, key=lambda q: q.question_order):
                for i, answer in enumerate(sorted(question.answers, key=lambda a: a.answer_order)):
                    if i == 0:
                        writer.writerow([
                            quiz.title,
                            quiz.description,
                            question.question_order,
                            question.question_text,
                            question.time_limit,
                            question.points,
                            answer.answer_text,
                            'Yes' if answer.is_correct else 'No',
                            answer.answer_order
                        ])
                    else:
                        writer.writerow([
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            answer.answer_text,
                            'Yes' if answer.is_correct else 'No',
                            answer.answer_order
                        ])
        
        csv_data = output.getvalue()
        return send_file(
            io.BytesIO(csv_data.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'quizzes_export_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.csv'
        )
    
    return jsonify({'error': 'Invalid format. Use "json" or "csv"'}), 400

@app.route('/api/admin/<int:admin_id>/quizzes/import', methods=['POST'])
def import_quiz(admin_id):
    """Import quiz from JSON or CSV file"""
    admin = Admin.query.get(admin_id)
    
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Verify the requesting user is the admin
    request_admin_id = request.form.get('admin_id', type=int)
    if not request_admin_id or request_admin_id != admin_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if file is provided
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file:
        return jsonify({'error': 'No file provided'}), 400
    
    try:
        # Determine file type
        filename = file.filename.lower()
        
        if filename.endswith('.json'):
            # Parse JSON
            content = file.read().decode('utf-8')
            data = json.loads(content)
            
            # Handle both single quiz and multiple quizzes
            if isinstance(data, dict) and 'title' in data:
                # Single quiz
                quizzes = [data]
            elif isinstance(data, list):
                # Multiple quizzes
                quizzes = data
            else:
                return jsonify({'error': 'Invalid JSON format'}), 400
        
        elif filename.endswith('.csv'):
            # Parse CSV
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            quizzes = {}
            current_quiz = None
            current_question = None
            
            for row in reader:
                # Skip empty rows
                if not any(row.values()):
                    continue
                
                quiz_title = row.get('Quiz Title', '').strip()
                quiz_desc = row.get('Description', '').strip()
                
                if quiz_title:
                    if quiz_title not in quizzes:
                        quizzes[quiz_title] = {
                            'title': quiz_title,
                            'description': quiz_desc,
                            'questions': []
                        }
                        current_quiz = quizzes[quiz_title]
                
                if current_quiz:
                    question_text = row.get('Question Text', '').strip()
                    if question_text:
                        # New question
                        question_order = int(row.get('Question Order', 1))
                        time_limit = int(row.get('Time Limit (sec)', 30))
                        points = int(row.get('Points', 100))
                        
                        current_question = {
                            'question_text': question_text,
                            'question_order': question_order,
                            'time_limit': time_limit,
                            'points': points,
                            'answers': []
                        }
                        current_quiz['questions'].append(current_question)
                    
                    # Add answer if present
                    answer_text = row.get('Answer Text', '').strip()
                    if answer_text and current_question:
                        is_correct = row.get('Is Correct', 'No').strip().lower() in ['yes', 'true', '1']
                        answer_order = int(row.get('Answer Order', 0))
                        
                        current_question['answers'].append({
                            'answer_text': answer_text,
                            'is_correct': is_correct,
                            'answer_order': answer_order
                        })
            
            quizzes = list(quizzes.values())
        
        else:
            return jsonify({'error': 'Unsupported file format. Use JSON or CSV'}), 400
        
        # Import quizzes
        imported_count = 0
        errors = []
        
        for quiz_data in quizzes:
            try:
                # Create quiz
                new_quiz = Quiz(
                    admin_id=admin_id,
                    title=quiz_data.get('title', 'Imported Quiz'),
                    description=quiz_data.get('description', '')
                )
                db.session.add(new_quiz)
                db.session.flush()  # Get quiz_id without committing
                
                # Add questions
                for question_data in quiz_data.get('questions', []):
                    new_question = Question(
                        quiz_id=new_quiz.quiz_id,
                        question_text=question_data.get('question_text', ''),
                        question_order=question_data.get('question_order', 0),
                        time_limit=question_data.get('time_limit', 30),
                        points=question_data.get('points', 100)
                    )
                    db.session.add(new_question)
                    db.session.flush()
                    
                    # Add answers
                    for answer_data in question_data.get('answers', []):
                        new_answer = Answer(
                            question_id=new_question.question_id,
                            answer_text=answer_data.get('answer_text', ''),
                            is_correct=answer_data.get('is_correct', False),
                            answer_order=answer_data.get('answer_order', 0)
                        )
                        db.session.add(new_answer)
                
                db.session.commit()
                imported_count += 1
            
            except Exception as e:
                db.session.rollback()
                errors.append(f"Failed to import '{quiz_data.get('title', 'Unknown')}': {str(e)}")
        
        if imported_count == 0:
            return jsonify({'error': 'No quizzes were imported', 'details': errors}), 400
        
        response = {
            'message': f'Successfully imported {imported_count} quiz(zes)',
            'imported_count': imported_count
        }
        
        if errors:
            response['warnings'] = errors
        
        return jsonify(response), 200
    
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)