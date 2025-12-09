from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admin'
    
    admin_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='admin', lazy=True)
    game_sessions = db.relationship('GameSession', backref='host', lazy=True)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    quiz_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.admin_id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    game_sessions = db.relationship('GameSession', backref='quiz', lazy=True)

class Question(db.Model):
    __tablename__ = 'questions'
    
    question_id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.quiz_id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_order = db.Column(db.Integer, nullable=False)
    time_limit = db.Column(db.Integer, default=30)
    points = db.Column(db.Integer, default=100)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')
    participant_answers = db.relationship('ParticipantAnswer', backref='question', lazy=True)

class Answer(db.Model):
    __tablename__ = 'answers'
    
    answer_id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.question_id'), nullable=False)
    answer_text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    answer_order = db.Column(db.Integer, nullable=False)
    
    # Relationships
    participant_answers = db.relationship('ParticipantAnswer', backref='answer', lazy=True)

class GameSession(db.Model):
    __tablename__ = 'game_sessions'
    
    game_session_id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.quiz_id'), nullable=False)
    game_code = db.Column(db.String(10), unique=True, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.admin_id'), nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, active, completed
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    
    # Relationships
    participants = db.relationship('Participant', backref='game_session', lazy=True, cascade='all, delete-orphan')

class Participant(db.Model):
    __tablename__ = 'participants'
    
    participant_id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.game_session_id'), nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    answers = db.relationship('ParticipantAnswer', backref='participant', lazy=True, cascade='all, delete-orphan')

class ParticipantAnswer(db.Model):
    __tablename__ = 'participant_answers'
    
    participant_answer_id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.participant_id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.question_id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.answer_id'), nullable=False)
    time_taken = db.Column(db.Integer)  # in seconds
    points_earned = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))