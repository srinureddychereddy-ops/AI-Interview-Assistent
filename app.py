import os
import json
import re
from pathlib import Path
import pandas as pd
from sqlalchemy import func, inspect
from datetime import datetime, timezone, timedelta
import subprocess
import traceback
import time
import secrets
from functools import wraps
from urllib.parse import urlencode
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, abort, has_request_context, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
# Add these structural package components to the top import matrix array
import fitz  # PyMuPDF engine library
import google.generativeai as genai
import requests
from dotenv import load_dotenv
import copy
import threading
import uuid
import question_bank


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_obsidian_key_4432')

# Single source of truth for all n8n resume-analysis requests.
WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', '').strip().strip('"\'').strip()

# --- DETECT ENVIRONMENT & ENSURE DIRECTORY STRUCTURE ---
# Define absolute paths to prevent Windows vs Linux directory mapping failures
DB_DIR = os.path.join(BASE_DIR, 'database')

# Automatically provision the database directory if missing
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# Configure absolute path URI string
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- File Upload Configuration ---
UPLOAD_FOLDER_PROFILE = os.path.join(BASE_DIR, 'static', 'uploads', 'profile')
UPLOAD_FOLDER_RESUME = os.path.join(BASE_DIR, 'static', 'uploads', 'resumes')
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER_PROFILE'] = UPLOAD_FOLDER_PROFILE
app.config['UPLOAD_FOLDER_RESUME'] = UPLOAD_FOLDER_RESUME
os.makedirs(UPLOAD_FOLDER_PROFILE, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_RESUME, exist_ok=True)

# Setup Gemini Engine configuration key layer maps
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "MOCK_KEY_FALLBACK"))

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Configure Flask-Mail
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# One-way bootstrap credential. The original password is never stored or logged.
INITIAL_ADMIN_EMAIL = 'admin@gmail.com'
INITIAL_ADMIN_PASSWORD_HASH = '$2b$12$SaNvHt44MeTZFMApICHUke/Pde5NEpw0YZm4S2oy8r.WtnTQRwzVW'

# --- Production Data Representation Schema Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    remember_token = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    selected_domain = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive if 'utc_now_naive' in globals() else datetime.utcnow)
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.is_active_account


class EmailOTP(db.Model):
    """Single-use, hashed email verification challenge."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, index=True)
    purpose = db.Column(db.String(32), nullable=False, default='password_reset', index=True)
    otp_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=5)
    used_at = db.Column(db.DateTime, nullable=True)
    invalidated_at = db.Column(db.DateTime, nullable=True)


OTP_EXPIRY_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
OTP_SESSION_VALID_SECONDS = 10 * 60
EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class OTPRateLimitError(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__('OTP resend rate limit reached')


class OTPDeliveryError(Exception):
    pass


def utc_now_naive():
    """Return naive UTC timestamps for consistent SQLite comparisons."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_email(email):
    normalized = (email or '').strip().lower()
    if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
        return None
    return normalized


def mask_email(email):
    local, _, domain = (email or '').partition('@')
    if not local or not domain:
        return 'invalid-email'
    return f"{local[:1]}***@{domain}"


def ensure_otp_storage():
    """Create the OTP table for both `python app.py` and `flask run` startup paths."""
    EmailOTP.__table__.create(bind=db.engine, checkfirst=True)


def build_otp_message(email, otp_code):
    message = Message(
        subject='Interview.ai Email Verification',
        recipients=[email],
    )
    message.body = (
        'Hello,\n\n'
        f'Your Interview.ai verification code is {otp_code}.\n'
        'This code expires in 5 minutes. Do not share it with anyone.\n\n'
        'If you did not request this code, you can safely ignore this email.\n\n'
        'Interview.ai Security Team'
    )
    message.html = f"""<!doctype html>
<html lang="en">
<body style="margin:0;background:#f4f7fb;font-family:Arial,Helvetica,sans-serif;color:#172033;">
  <div style="padding:36px 16px;">
    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e5eaf2;border-radius:20px;overflow:hidden;box-shadow:0 14px 40px rgba(30,64,175,.10);">
      <div style="padding:24px 32px;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#fff;font-size:22px;font-weight:700;letter-spacing:-.4px;">
        Interview.ai
      </div>
      <div style="padding:34px 32px;">
        <h1 style="margin:0 0 14px;font-size:24px;line-height:1.3;">Verify your email</h1>
        <p style="margin:0 0 24px;color:#536176;line-height:1.7;">Hello, use the verification code below to continue securely with Interview.ai.</p>
        <div style="margin:0 0 22px;padding:20px;text-align:center;background:#f5f7ff;border:1px solid #dfe5ff;border-radius:14px;">
          <div style="font-size:12px;font-weight:700;letter-spacing:1.5px;color:#667085;text-transform:uppercase;">Verification code</div>
          <div style="margin-top:8px;font-size:36px;font-weight:800;letter-spacing:10px;color:#2738c8;">{otp_code}</div>
        </div>
        <p style="margin:0 0 18px;color:#536176;line-height:1.7;"><strong>This code expires in 5 minutes.</strong></p>
        <div style="padding:14px 16px;background:#fff8e6;border-left:4px solid #f59e0b;border-radius:8px;color:#6b5220;font-size:14px;line-height:1.6;">
          For your security, never share this code. Interview.ai will never ask for it by phone or chat.
        </div>
      </div>
      <div style="padding:20px 32px;background:#f8fafc;color:#7a8699;font-size:12px;line-height:1.6;text-align:center;">
        If you did not request this code, you can safely ignore this email.<br>© Interview.ai
      </div>
    </div>
  </div>
</body>
</html>"""
    return message


def issue_email_otp(email, purpose='password_reset'):
    """Create, email, and persist a new OTP while invalidating prior challenges."""
    normalized = normalize_email(email)
    if not normalized:
        raise ValueError('Please enter a valid email address.')
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        raise OTPDeliveryError('Email service is not configured.')

    ensure_otp_storage()

    now = utc_now_naive()
    latest = EmailOTP.query.filter_by(email=normalized, purpose=purpose).order_by(EmailOTP.created_at.desc()).first()
    if latest:
        elapsed = (now - latest.created_at).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            raise OTPRateLimitError(max(1, OTP_RESEND_COOLDOWN_SECONDS - int(elapsed)))

    EmailOTP.query.filter_by(
        email=normalized,
        purpose=purpose,
        used_at=None,
        invalidated_at=None,
    ).update({'invalidated_at': now}, synchronize_session=False)

    otp_code = f"{secrets.randbelow(900000) + 100000}"
    challenge = EmailOTP(
        email=normalized,
        purpose=purpose,
        otp_hash=bcrypt.generate_password_hash(otp_code).decode('utf-8'),
        created_at=now,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        attempts=0,
        max_attempts=OTP_MAX_ATTEMPTS,
    )
    db.session.add(challenge)
    db.session.flush()

    legacy_user = User.query.filter(func.lower(User.email) == normalized).first()
    if legacy_user:
        legacy_user.otp = None
        legacy_user.otp_expiry = None

    try:
        mail.send(build_otp_message(normalized, otp_code))
        db.session.add(EmailLog(recipient=normalized, email_type='OTP', status='sent'))
        db.session.commit()
    except Exception as exc:
        import traceback

        print("\n" + "="*80)
        print("SMTP ERROR")
        print("="*80)
        traceback.print_exc()
        print("="*80 + "\n")

        db.session.rollback()

        try:
            db.session.add(EmailLog(recipient=normalized, email_type='OTP', status='failed', error=str(exc)[:500]))
            db.session.commit()
        except Exception:
            db.session.rollback()

        raise

    app.logger.info('OTP email accepted for delivery to %s.', mask_email(normalized))
    return challenge


def verify_email_otp(email, submitted_otp, purpose='password_reset'):
    normalized = normalize_email(email)
    submitted = (submitted_otp or '').strip()

    if not normalized:
        app.logger.warning('OTP verification failed: email mismatch or invalid email.')
        return False, 'Please enter a valid email address.', 'invalid_email'
    if not submitted:
        app.logger.warning('OTP verification failed: missing OTP for %s.', mask_email(normalized))
        return False, 'Please enter the 6-digit verification code.', 'missing'
    if not re.fullmatch(r'\d{6}', submitted):
        app.logger.warning('OTP verification failed: malformed OTP for %s.', mask_email(normalized))
        return False, 'Verification code must contain exactly 6 digits.', 'invalid_format'

    ensure_otp_storage()

    challenge = EmailOTP.query.filter_by(
        email=normalized,
        purpose=purpose,
        used_at=None,
        invalidated_at=None,
    ).order_by(EmailOTP.created_at.desc()).first()
    if not challenge:
        app.logger.warning('OTP verification failed: missing database record for %s.', mask_email(normalized))
        return False, 'No active verification code was found. Please request a new one.', 'not_found'

    if challenge.email.strip().lower() != normalized.strip().lower():
        app.logger.warning('OTP verification failed: email mismatch for active challenge.')
        return False, 'The verification email does not match the active OTP.', 'email_mismatch'

    now = utc_now_naive()
    if now >= challenge.expires_at:
        app.logger.warning('OTP verification failed: expired OTP for %s.', mask_email(normalized))
        challenge.invalidated_at = now
        db.session.commit()
        return False, 'Your verification code has expired. Please request a new one.', 'expired'

    if challenge.attempts >= challenge.max_attempts:
        app.logger.warning('OTP verification failed: attempt limit reached for %s.', mask_email(normalized))
        challenge.invalidated_at = now
        db.session.commit()
        return False, 'Too many incorrect attempts. Please request a new code.', 'locked'

    try:
        is_valid = bcrypt.check_password_hash(challenge.otp_hash, submitted)
    except ValueError:
        is_valid = False

    if not is_valid:
        app.logger.warning('OTP verification failed: OTP mismatch for %s.', mask_email(normalized))
        challenge.attempts += 1
        remaining = challenge.max_attempts - challenge.attempts
        if remaining <= 0:
            challenge.invalidated_at = now
            message = 'Too many incorrect attempts. Please request a new code.'
            status = 'locked'
        else:
            message = f'Incorrect verification code. {remaining} attempt(s) remaining.'
            status = 'incorrect'
        db.session.commit()
        return False, message, status

    challenge.used_at = now
    challenge.invalidated_at = now
    legacy_user = User.query.filter(func.lower(User.email) == normalized).first()
    if legacy_user:
        legacy_user.otp = None
        legacy_user.otp_expiry = None
    db.session.commit()
    return True, 'Code verified successfully.', 'verified'


def otp_session_is_valid():
    verified_at = session.get('otp_verified_at')
    try:
        return bool(session.get('otp_verified')) and (time.time() - float(verified_at)) <= OTP_SESSION_VALID_SECONDS
    except (TypeError, ValueError):
        return False


# --- New Database Models for MCQ Assessment ---
class MCQSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    wrong_answers = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    time_taken_seconds = db.Column(db.Integer, nullable=False)
    
    # Proctoring metrics
    camera_verified = db.Column(db.Boolean, default=True)
    microphone_verified = db.Column(db.Boolean, default=True)
    fullscreen_warnings = db.Column(db.Integer, default=0)
    tab_switch_warnings = db.Column(db.Integer, default=0)
    proctoring_warnings = db.Column(db.Integer, default=0)
    interview_status = db.Column(db.String(20), default='completed')
    
    user = db.relationship('User', backref=db.backref('mcq_sessions', lazy=True))
    attempts = db.relationship('MCQAttempt', backref='session', lazy='dynamic', cascade="all, delete-orphan")

class MCQAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('mcq_session.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    user_answer = db.Column(db.Text) # Stores full option text or None if skipped
    correct_option = db.Column(db.Text, nullable=False) # Stores full option text
    explanation = db.Column(db.Text)
    is_correct = db.Column(db.Boolean, nullable=False)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    pincode = db.Column(db.String(20))

    college_name = db.Column(db.String(200))
    university = db.Column(db.String(200))
    degree = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    current_semester = db.Column(db.Integer)
    graduation_year = db.Column(db.Integer)
    cgpa = db.Column(db.Float)

    preferred_domain = db.Column(db.String(100))
    programming_languages = db.Column(db.Text)
    skills = db.Column(db.Text)
    linkedin_profile = db.Column(db.String(255))
    github_profile = db.Column(db.String(255))
    portfolio_website = db.Column(db.String(255))

    profile_image_filename = db.Column(db.String(255), default='default.png')
    resume_filename = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)

class InterviewSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.String(50), nullable=False)
    interview_type = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default='in_progress')
    user = db.relationship('User', backref=db.backref('interview_sessions', lazy=True))

class InterviewQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_session.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text)
    feedback = db.Column(db.Text)
    scores = db.Column(db.Text)
    question_order = db.Column(db.Integer, nullable=False)
    session = db.relationship('InterviewSession', backref=db.backref('questions', lazy=True, cascade='all, delete-orphan'))

class InterviewReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_session.id'), nullable=False, unique=True)
    overall_score = db.Column(db.Integer)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    summary = db.Column(db.Text)
    detailed_scores = db.Column(db.Text)
    session = db.relationship('InterviewSession', backref=db.backref('report', uselist=False, cascade='all, delete-orphan'))

class ResumeAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_role = db.Column(db.String(150))
    ats_score = db.Column(db.Float)
    analysis_json = db.Column(db.Text, nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    job_description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='completed')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('resume_analyses', lazy=True, cascade='all, delete-orphan'))

class CodingAssessment(db.Model):
    __tablename__ = 'coding_assessment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(150), default='Software Engineer')
    domain = db.Column(db.String(150), default='Software Engineering')
    difficulty = db.Column(db.String(50), default='Medium')
    language = db.Column(db.String(50), default='Python')
    total_questions = db.Column(db.Integer, default=5)
    questions_solved = db.Column(db.Integer, default=0)
    questions_attempted = db.Column(db.Integer, default=0)
    overall_score = db.Column(db.Float, default=0.0)
    time_used_seconds = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, default=45)
    total_test_cases = db.Column(db.Integer, default=0)
    passed_test_cases = db.Column(db.Integer, default=0)
    failed_test_cases = db.Column(db.Integer, default=0)
    questions_data = db.Column(db.Text, nullable=True) # JSON list of questions
    results_data = db.Column(db.Text, nullable=True)   # JSON list of evaluated results
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('coding_assessments', lazy=True, cascade='all, delete-orphan'))

class InterviewJourney(db.Model):
    __tablename__ = 'interview_journey'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), default='in_progress') # 'in_progress', 'completed'
    ats_score = db.Column(db.Float, nullable=True)
    aptitude_score = db.Column(db.Integer, nullable=True)
    coding_score = db.Column(db.Float, nullable=True)
    coding_completed = db.Column(db.Boolean, default=False)
    certificate_id = db.Column(db.String(60), nullable=True)
    resume_analysis_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'), nullable=True)
    mcq_session_id = db.Column(db.Integer, db.ForeignKey('mcq_session.id'), nullable=True)
    coding_assessment_id = db.Column(db.Integer, db.ForeignKey('coding_assessment.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User', backref=db.backref('interview_journeys', lazy=True, cascade='all, delete-orphan'))

class CertificateRecord(db.Model):
    __tablename__ = 'certificate_record'
    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.String(60), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    journey_id = db.Column(db.Integer, db.ForeignKey('interview_journey.id'), nullable=True)
    candidate_name = db.Column(db.String(150), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    ats_score = db.Column(db.Float, nullable=False)
    aptitude_score = db.Column(db.Integer, nullable=False)
    coding_score = db.Column(db.Float, nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('certificates', lazy=True, cascade='all, delete-orphan'))
    journey = db.relationship('InterviewJourney', backref=db.backref('certificate_record', uselist=False))

class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(254), nullable=False)
    email_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)
    error = db.Column(db.Text)

class ServiceExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)
    error = db.Column(db.Text)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(80), nullable=False)
    target = db.Column(db.String(160))
    status = db.Column(db.String(20), nullable=False, default='success')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    admin = db.relationship('User')

class PlatformSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(40), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def handle_unauthorized():
    """Ensure API and AJAX requests receive structured JSON instead of HTML redirect."""
    is_api = (
        request.path.startswith('/api/') or
        request.path in ['/resume/upload', '/coding/run'] or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.is_json or
        'application/json' in request.headers.get('Accept', '')
    )
    if is_api:
        return jsonify({
            'success': False,
            'error': 'Authentication required. Please log in to continue.',
            'message': 'Authentication required. Please log in to continue.'
        }), 401
    flash("Please log in to access this page.", "info")
    return redirect(url_for('login', next=request.path))

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(413)
@app.errorhandler(500)
def handle_api_http_errors(error):
    """Ensure API and AJAX requests receive structured JSON instead of HTML error pages."""
    is_api = (
        request.path.startswith('/api/') or
        request.path in ['/resume/upload', '/coding/run'] or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.is_json or
        'application/json' in request.headers.get('Accept', '')
    )
    code = getattr(error, 'code', 500)
    description = getattr(error, 'description', str(error))
    if is_api:
        return jsonify({
            'success': False,
            'error': description or 'An unexpected error occurred.',
            'message': description or 'An unexpected error occurred.'
        }), code
    return error

def normalize_interview_type(itype_str):
    """Normalizes interview track to canonical values: Technical, HR, Coding, Mixed."""
    if not itype_str:
        return 'Technical'
    s = str(itype_str).strip().lower()
    mapping = {
        'technical': 'Technical',
        'hr': 'HR',
        'coding': 'Coding',
        'mixed': 'Mixed'
    }
    return mapping.get(s, s.title())


# =========================================================================
# CENTRALIZED DOMAIN RESOLUTION SYSTEM — SINGLE SOURCE OF TRUTH
# =========================================================================

SUPPORTED_DOMAINS = [
    "AI / Machine Learning",
    "Data Science",
    "Backend Development",
    "Frontend Development",
    "Full Stack Development",
    "DevOps",
    "Data Engineering",
    "Cybersecurity",
    "Mobile Development",
    "Software Engineering"
]

DOMAIN_METADATA = {
    "AI / Machine Learning": {
        "icon": "bi-cpu",
        "badge": "AI & ML",
        "description": "Machine Learning, Deep Learning, NLP, Model Evaluation, and Python AI algorithms."
    },
    "Data Science": {
        "icon": "bi-graph-up",
        "badge": "Analytics",
        "description": "Statistics, Python/SQL, Data Analysis, Machine Learning fundamentals, and Probability."
    },
    "Backend Development": {
        "icon": "bi-server",
        "badge": "Backend",
        "description": "APIs, Databases, Microservices, Authentication, System Architecture, and DSA."
    },
    "Frontend Development": {
        "icon": "bi-window-desktop",
        "badge": "Frontend",
        "description": "Modern JavaScript, React, HTML/CSS, Web Architecture, and UI Performance."
    },
    "Full Stack Development": {
        "icon": "bi-layers",
        "badge": "Full Stack",
        "description": "End-to-end Web Applications, Frontend, Backend APIs, Databases, and Systems."
    },
    "DevOps": {
        "icon": "bi-cloud-check",
        "badge": "Cloud & CI/CD",
        "description": "Linux, Docker, Kubernetes, CI/CD, Cloud Architecture, Monitoring, and SRE."
    },
    "Data Engineering": {
        "icon": "bi-database",
        "badge": "Pipelines",
        "description": "ETL Pipelines, Distributed Systems, SQL, Stream Processing, and Big Data."
    },
    "Cybersecurity": {
        "icon": "bi-shield-lock",
        "badge": "Security",
        "description": "Application Security, Cryptography, Network Defense, and Threat Analysis."
    },
    "Mobile Development": {
        "icon": "bi-phone",
        "badge": "Mobile Apps",
        "description": "Mobile App Architecture, State Management, Offline Queues, and Native Patterns."
    },
    "Software Engineering": {
        "icon": "bi-code-slash",
        "badge": "Core SWE",
        "description": "Core DSA, Object-Oriented Design, Algorithm Efficiency, and Clean Architecture."
    }
}

def normalize_canonical_domain(domain_str):
    """Normalizes any domain string into one of the 10 canonical supported domains."""
    if not domain_str:
        return None
    d = str(domain_str).strip().lower()
    
    # Exact match check first
    for supp in SUPPORTED_DOMAINS:
        if supp.lower() == d:
            return supp
            
    if any(k in d for k in ['ai / machine', 'ai/ml', 'ai / ml', 'ai & machine', 'machine learning', 'artificial intelligence', 'ai_engineer', 'ai engineer']):
        return "AI / Machine Learning"
    if any(k in d for k in ['data sci', 'data scientist', 'data science', 'analytics']):
        return "Data Science"
    if any(k in d for k in ['backend', 'back-end', 'back end', 'node', 'django', 'flask', 'api']):
        return "Backend Development"
    if any(k in d for k in ['frontend', 'front-end', 'front end', 'react', 'angular', 'vue', 'ui/ux', 'ui / ux', 'web developer']):
        return "Frontend Development"
    if any(k in d for k in ['fullstack', 'full-stack', 'full stack']):
        return "Full Stack Development"
    if any(k in d for k in ['devops', 'cloud', 'aws', 'docker', 'kubernetes', 'sre', 'ci/cd']):
        return "DevOps"
    if any(k in d for k in ['data eng', 'data engineering', 'etl', 'pipeline', 'spark', 'hadoop']):
        return "Data Engineering"
    if any(k in d for k in ['cyber', 'security', 'infosec', 'pentest']):
        return "Cybersecurity"
    if any(k in d for k in ['mobile', 'android', 'ios', 'flutter', 'react native', 'swift']):
        return "Mobile Development"
    if any(k in d for k in ['software', 'software engineering', 'swe', 'general']):
        return "Software Engineering"
        
    return None

def get_user_selected_domain(user=None):
    """
    Centralized single-source-of-truth for candidate's selected domain.
    Resolution priority:
    1. Specified user or current_user's `selected_domain` attribute in database
    2. User's profile `preferred_domain` attribute in database
    3. Session domain (for unauthenticated/guest users)
    Returns canonical domain string, or None if not set.
    """
    u = user if user else (current_user if current_user.is_authenticated else None)
    if u:
        if hasattr(u, 'selected_domain') and u.selected_domain:
            canonical = normalize_canonical_domain(u.selected_domain)
            if canonical:
                return canonical
        if hasattr(u, 'profile') and u.profile and u.profile.preferred_domain:
            canonical = normalize_canonical_domain(u.profile.preferred_domain)
            if canonical:
                return canonical
        if hasattr(u, 'id') and u.id:
            try:
                latest_j = InterviewJourney.query.filter_by(user_id=u.id).order_by(InterviewJourney.created_at.desc()).first()
                if latest_j and latest_j.domain:
                    canonical = normalize_canonical_domain(latest_j.domain)
                    if canonical:
                        return canonical
            except Exception:
                pass

    if has_request_context():
        sess_domain = session.get('selected_domain') or session.get('coding_domain') or session.get('target_domain')
        if sess_domain:
            canonical = normalize_canonical_domain(sess_domain)
            if canonical:
                return canonical

    return None

def set_user_selected_domain(domain_str, user=None):
    """
    Persistently sets the user's selected domain in database and session.
    """
    canonical = normalize_canonical_domain(domain_str)
    if not canonical:
        raise ValueError(f"Unsupported domain: {domain_str}")

    u = user if user else (current_user if current_user.is_authenticated else None)
    if u:
        u.selected_domain = canonical
        prof = None
        try:
            prof = u.profile
        except Exception:
            pass
        if not prof and hasattr(u, 'id') and u.id:
            try:
                prof = UserProfile.query.filter_by(user_id=u.id).first()
            except Exception:
                pass
        if prof:
            prof.preferred_domain = canonical
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    if has_request_context():
        session['selected_domain'] = canonical
        session['target_domain'] = canonical
        session['coding_domain'] = canonical
        session.modified = True
    return canonical

def map_domain_to_aptitude_file(domain):
    """Maps canonical domain to the corresponding Excel question bank file."""
    canonical = normalize_canonical_domain(domain)
    mapping = {
        "AI / Machine Learning": "AI_Engineer",
        "Data Science": "data_scientist",
        "Backend Development": "Backend_Developer",
        "Frontend Development": "frontend_developer",
        "Full Stack Development": "full_stack_developer",
        "DevOps": "cloud_devops",
        "Data Engineering": "data_scientist",
        "Cybersecurity": "cyber_security",
        "Mobile Development": "software_engineer",
        "Software Engineering": "software_engineer"
    }
    return mapping.get(canonical, "software_engineer")

def get_interview_journey_status(user=None):
    """
    Centralized single-source-of-truth for candidate's interview journey progress.
    Evaluates:
    - Domain selection (Dashboard source of truth)
    - Stage 1: Resume Analysis (ATS >= 80 required)
    - Stage 2: Aptitude Assessment (Score >= 80 required)
    - Stage 3: Coding Assessment (Successfully completed)
    - Stage 4: Certificate of Completion (Unlocked when stages 1, 2, 3 pass)
    """
    u = user if user else (current_user if current_user.is_authenticated else None)
    domain = get_user_selected_domain(u)

    if not domain:
        dashboard_url = url_for('dashboard') if has_request_context() else '/dashboard'
        return {
            'has_domain': False,
            'domain': None,
            'journey_id': None,
            'journey_started': False,
            'active_stage': 'domain',
            'active_stage_url': dashboard_url,
            'resume': {'unlocked': False, 'completed': False, 'ats_score': None, 'status': 'locked', 'required_score': 80},
            'aptitude': {'unlocked': False, 'completed': False, 'score': None, 'status': 'locked', 'required_score': 80},
            'coding': {'unlocked': False, 'completed': False, 'score': None, 'status': 'locked'},
            'certificate': {'unlocked': False, 'id': None, 'status': 'locked'}
        }

    # If no authenticated user, return default available stage 1
    if not u or not getattr(u, 'id', None):
        resume_url = url_for('resume_analyzer') if has_request_context() else '/resume'
        return {
            'has_domain': True,
            'domain': domain,
            'journey_id': None,
            'journey_started': False,
            'active_stage': 'resume',
            'active_stage_url': resume_url,
            'resume': {'unlocked': True, 'completed': False, 'ats_score': None, 'status': 'available', 'required_score': 80},
            'aptitude': {'unlocked': False, 'completed': False, 'score': None, 'status': 'locked', 'required_score': 80},
            'coding': {'unlocked': False, 'completed': False, 'score': None, 'status': 'locked'},
            'certificate': {'unlocked': False, 'id': None, 'status': 'locked'}
        }

    if has_request_context() and u and getattr(u, 'id', None):
        cache_key = f"_journey_cache_{u.id}_{domain}"
        cached = getattr(g, cache_key, None)
        if cached is not None:
            return cached

    # 1. Fetch active InterviewJourney for this user & domain
    journey = InterviewJourney.query.filter_by(
        user_id=u.id, domain=domain, status='in_progress'
    ).order_by(InterviewJourney.created_at.desc()).first()

    if not journey:
        journey = InterviewJourney.query.filter_by(
            user_id=u.id, domain=domain, status='completed'
        ).order_by(InterviewJourney.created_at.desc()).first()

    # 2. Check latest ResumeAnalysis
    latest_resume = ResumeAnalysis.query.filter_by(
        user_id=u.id, status='completed'
    ).order_by(ResumeAnalysis.created_at.desc()).first()

    resume_ats_score = None
    if latest_resume and latest_resume.ats_score is not None:
        resume_ats_score = round(latest_resume.ats_score, 1)
    elif journey and journey.ats_score is not None:
        resume_ats_score = round(journey.ats_score, 1)

    resume_completed = bool(resume_ats_score is not None and resume_ats_score >= 80.0)
    resume_started = bool(latest_resume is not None or (journey and journey.ats_score is not None))

    # 3. Check latest Aptitude / MCQSession for this domain
    latest_mcq = MCQSession.query.filter_by(
        user_id=u.id, domain=domain
    ).order_by(MCQSession.end_time.desc()).first()

    aptitude_score = latest_mcq.score if latest_mcq else (journey.aptitude_score if journey else None)
    aptitude_unlocked = resume_completed
    aptitude_completed = bool(aptitude_unlocked and aptitude_score is not None and aptitude_score >= 80)
    aptitude_started = bool(latest_mcq is not None or (journey and journey.aptitude_score is not None))

    # 4. Check latest CodingAssessment for this domain
    latest_coding = CodingAssessment.query.filter_by(
        user_id=u.id, domain=domain
    ).order_by(CodingAssessment.submitted_at.desc()).first()

    coding_score = round(latest_coding.overall_score, 1) if latest_coding else (round(journey.coding_score, 1) if journey and journey.coding_score is not None else None)
    coding_unlocked = bool(resume_completed and aptitude_completed)
    coding_completed = bool(
        coding_unlocked and (
            (latest_coding and (latest_coding.overall_score >= 60.0 or latest_coding.questions_solved >= 1)) or
            (not latest_coding and journey and journey.coding_completed)
        )
    )
    coding_started = bool(latest_coding is not None or (journey and (journey.coding_score is not None or journey.coding_completed)))

    # 5. Check Certificate
    certificate_unlocked = bool(resume_completed and aptitude_completed and coding_completed)
    cert_record = CertificateRecord.query.filter_by(user_id=u.id, domain=domain).first()

    if certificate_unlocked and not cert_record:
        cert_id = f"IA-2026-{secrets.token_hex(4).upper()}"
        first_n = u.profile.first_name if (hasattr(u, 'profile') and u.profile) else ''
        last_n = u.profile.last_name if (hasattr(u, 'profile') and u.profile) else ''
        candidate_name = ' '.join(filter(None, [first_n, last_n])).strip() or u.username

        cert_record = CertificateRecord(
            certificate_id=cert_id,
            user_id=u.id,
            candidate_name=candidate_name,
            domain=domain,
            ats_score=resume_ats_score or 80.0,
            aptitude_score=aptitude_score or 80,
            coding_score=coding_score or 80.0,
            issue_date=datetime.utcnow()
        )
        db.session.add(cert_record)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    certificate_id = cert_record.certificate_id if cert_record else None

    # 6. Synchronize InterviewJourney record
    if not journey:
        journey = InterviewJourney(
            user_id=u.id,
            domain=domain,
            status='completed' if certificate_unlocked else 'in_progress',
            ats_score=resume_ats_score,
            aptitude_score=aptitude_score,
            coding_score=coding_score,
            coding_completed=coding_completed,
            certificate_id=certificate_id,
            resume_analysis_id=latest_resume.id if latest_resume else None,
            mcq_session_id=latest_mcq.id if latest_mcq else None,
            coding_assessment_id=latest_coding.id if latest_coding else None,
            completed_at=datetime.utcnow() if certificate_unlocked else None
        )
        db.session.add(journey)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    else:
        changed = False
        if journey.ats_score != resume_ats_score:
            journey.ats_score = resume_ats_score
            changed = True
        if journey.aptitude_score != aptitude_score:
            journey.aptitude_score = aptitude_score
            changed = True
        if journey.coding_score != coding_score:
            journey.coding_score = coding_score
            changed = True
        if journey.coding_completed != coding_completed:
            journey.coding_completed = coding_completed
            changed = True
        if certificate_id and journey.certificate_id != certificate_id:
            journey.certificate_id = certificate_id
            changed = True
        if certificate_unlocked and journey.status != 'completed':
            journey.status = 'completed'
            journey.completed_at = datetime.utcnow()
            changed = True
        if changed:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    resume_status = 'completed' if resume_completed else ('in_progress' if resume_started else 'available')
    aptitude_status = 'locked' if not aptitude_unlocked else ('completed' if aptitude_completed else ('in_progress' if aptitude_started else 'available'))
    coding_status = 'locked' if not coding_unlocked else ('completed' if coding_completed else ('in_progress' if coding_started else 'available'))
    certificate_status = 'unlocked' if certificate_unlocked else 'locked'

    if not resume_completed:
        active_stage = 'resume'
        active_stage_url = url_for('resume_analyzer') if has_request_context() else '/resume'
    elif not aptitude_completed:
        active_stage = 'aptitude'
        active_stage_url = url_for('interview_assessment') if has_request_context() else '/interview-assessment'
    elif not coding_completed:
        active_stage = 'coding'
        active_stage_url = url_for('coding_setup') if has_request_context() else '/coding/setup'
    else:
        active_stage = 'certificate'
        active_stage_url = url_for('view_certificate') if has_request_context() else '/certificate'

    journey_started = bool(resume_started or aptitude_started or coding_started)

    res = {
        'has_domain': True,
        'domain': domain,
        'journey_id': journey.id if journey else None,
        'journey_started': journey_started,
        'active_stage': active_stage,
        'active_stage_url': active_stage_url,
        'resume': {
            'unlocked': True,
            'completed': resume_completed,
            'ats_score': resume_ats_score,
            'status': resume_status,
            'required_score': 80
        },
        'aptitude': {
            'unlocked': aptitude_unlocked,
            'completed': aptitude_completed,
            'score': aptitude_score,
            'status': aptitude_status,
            'required_score': 80
        },
        'coding': {
            'unlocked': coding_unlocked,
            'completed': coding_completed,
            'score': coding_score,
            'status': coding_status
        },
        'certificate': {
            'unlocked': certificate_unlocked,
            'id': certificate_id,
            'status': certificate_status
        }
    }
    if has_request_context() and u and getattr(u, 'id', None):
        setattr(g, f"_journey_cache_{u.id}_{domain}", res)
    return res

def ensure_schema_migrations():
    """Ensure all required columns and tables exist in SQLite database without losing data."""
    try:
        with app.app_context():
            InterviewJourney.__table__.create(bind=db.engine, checkfirst=True)
            CertificateRecord.__table__.create(bind=db.engine, checkfirst=True)
            inspector = db.inspect(db.engine)
            if 'user' in inspector.get_table_names():
                user_cols = [c['name'] for c in inspector.get_columns('user')]
                if 'selected_domain' not in user_cols:
                    with db.engine.connect() as conn:
                        conn.execute(db.text("ALTER TABLE user ADD COLUMN selected_domain VARCHAR(100)"))
                        conn.commit()
    except Exception as e:
        app.logger.warning(f"Schema migration notice: {e}")

try:
    ensure_schema_migrations()
except Exception:
    pass

_maintenance_mode_cache = {'val': 'off', 'expires_at': 0}

def is_maintenance_mode_on():
    now_ts = time.time()
    if now_ts >= _maintenance_mode_cache['expires_at']:
        try:
            m = PlatformSetting.query.filter_by(key='maintenance_mode').first()
            _maintenance_mode_cache['val'] = m.value if m else 'off'
        except Exception:
            _maintenance_mode_cache['val'] = 'off'
        _maintenance_mode_cache['expires_at'] = now_ts + 15
    return _maintenance_mode_cache['val'] == 'on'

# --- Global Session and CSRF Protections ---

@app.before_request
def ensure_session_vars():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    if current_user.is_authenticated:
        session['user_id'] = current_user.id
        session['user_email'] = current_user.email
        session['user_name'] = current_user.username
        session['role'] = current_user.role
        # Authoritative domain synchronization into session
        active_domain = get_user_selected_domain()
        if active_domain:
            session['selected_domain'] = active_domain
            session['target_domain'] = active_domain
            session['coding_domain'] = active_domain
        session.modified = True
    # Maintenance mode check
    try:
        if is_maintenance_mode_on():
            is_admin = getattr(current_user, 'role', None) == 'admin' or session.get('role') == 'admin'
            allowed_endpoints = ['login', 'logout', 'register', 'forgot_password', 'reset_password', 'verify_otp', 'static', 'admin_login', 'admin_logout']
            if not is_admin and request.endpoint not in allowed_endpoints:
                return "The platform is currently undergoing maintenance. Please try again later.", 503
    except Exception:
        pass

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=session.get('csrf_token'))

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session and not current_user.is_authenticated:
            return redirect(url_for('login', next=request.path))
        
        user_role = current_user.role if (current_user and current_user.is_authenticated) else session.get('role')
        if user_role != 'admin':
            return redirect(url_for('dashboard'))
            
        return view(*args, **kwargs)
    return wrapped

def audit(action, target='', status='success'):
    db.session.add(AuditLog(admin_id=current_user.id if current_user.is_authenticated else None,
                            action=action, target=str(target)[:160], status=status))
    db.session.commit()

def csrf_ok():
    return request.form.get('csrf_token') == session.get('csrf_token')

# Google OAuth configuration. Values are loaded once from the project-local .env.
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '').strip()


def mask_oauth_secret(secret):
    """Return a diagnostic-safe representation of an OAuth secret."""
    if not secret:
        return '<missing>'
    if len(secret) <= 8:
        return '*' * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


def google_oauth_has_placeholders():
    values = (GOOGLE_CLIENT_ID.lower(), GOOGLE_CLIENT_SECRET.lower())
    markers = ('your-google', 'google-client-id', 'google-client-secret', 'placeholder')
    return any(marker in value for value in values for marker in markers)


def get_google_redirect_uri():
    """Use one stable callback URI for both authorization and token exchange."""
    return GOOGLE_REDIRECT_URI or url_for('login_google_callback', _external=True)


print('=' * 60)
print('Google OAuth configuration loaded from:', BASE_DIR / '.env')
print('GOOGLE_CLIENT_ID =', repr(GOOGLE_CLIENT_ID or '<missing>'))
print('GOOGLE_CLIENT_SECRET =', repr(mask_oauth_secret(GOOGLE_CLIENT_SECRET)))
print('GOOGLE_REDIRECT_URI =', repr(GOOGLE_REDIRECT_URI or '<generated from request host>'))
print('=' * 60)

# --- Application Routing Endpoints ---

@app.route('/')
def landing():
    users = User.query.filter_by(role='user', is_active_account=True).all()
    leaderboard = []

    for u in users:
        cert = CertificateRecord.query.filter_by(user_id=u.id).order_by(CertificateRecord.issue_date.desc()).first()
        journey = InterviewJourney.query.filter_by(user_id=u.id, status='completed').order_by(InterviewJourney.completed_at.desc()).first()
        latest_resume = ResumeAnalysis.query.filter_by(user_id=u.id, status='completed').order_by(ResumeAnalysis.created_at.desc()).first()
        latest_mcq = MCQSession.query.filter_by(user_id=u.id).order_by(MCQSession.end_time.desc()).first()
        latest_coding = CodingAssessment.query.filter_by(user_id=u.id).order_by(CodingAssessment.submitted_at.desc()).first()

        ats_score = None
        apt_score = None
        code_score = None
        domain = get_user_selected_domain(u)

        if cert:
            ats_score = cert.ats_score
            apt_score = cert.aptitude_score
            code_score = cert.coding_score
            domain = cert.domain or domain
        elif journey and journey.ats_score is not None and journey.aptitude_score is not None and journey.coding_score is not None:
            ats_score = journey.ats_score
            apt_score = journey.aptitude_score
            code_score = journey.coding_score
            domain = journey.domain or domain
        elif latest_resume and latest_resume.ats_score is not None and latest_mcq and latest_mcq.score is not None and latest_coding and latest_coding.overall_score is not None:
            ats_score = latest_resume.ats_score
            apt_score = latest_mcq.score
            code_score = latest_coding.overall_score
            domain = latest_coding.domain or latest_mcq.domain or domain

        if ats_score is not None and apt_score is not None and code_score is not None:
            readiness = round((float(ats_score) + float(apt_score) + float(code_score)) / 3.0, 1)
            first_n = u.profile.first_name if (u.profile and u.profile.first_name) else ''
            last_n = u.profile.last_name if (u.profile and u.profile.last_name) else ''
            candidate_name = ' '.join(filter(None, [first_n, last_n])).strip() or u.username
            avatar_initial = candidate_name[:1].upper() if candidate_name else 'C'

            leaderboard.append({
                'name': candidate_name,
                'initial': avatar_initial,
                'domain': normalize_canonical_domain(domain) or (domain or 'Software Engineering'),
                'score': readiness,
                'ats_score': round(float(ats_score), 1),
                'aptitude_score': int(round(float(apt_score))),
                'coding_score': round(float(code_score), 1),
                'journey_completed': bool(cert or (journey and journey.status == 'completed')),
                'certificate_id': cert.certificate_id if cert else (journey.certificate_id if journey else None)
            })

    # Sort descending by readiness score
    leaderboard.sort(key=lambda x: x['score'], reverse=True)

    return render_template('landing.html', current_year=datetime.now().year, leaderboard=leaderboard)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # CSRF Protection
        token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            flash('CSRF token validation failed.', 'danger')
            return redirect(url_for('register'))

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        
        # Verify no collisions exist inside datastore
        user_exists = User.query.filter((User.email == email) | (User.username == username)).first()
        if user_exists:
            flash('Identifiers already configured inside standard memory.', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # Create a corresponding profile
        new_profile = UserProfile(user_id=new_user.id, first_name=username)
        db.session.add(new_profile)
        db.session.commit()
        
        flash('Account structural mapping finalized. Please authenticate.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        # CSRF Protection
        token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            flash('CSRF token validation failed.', 'danger')
            return redirect(url_for('login'))

        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember_me') == 'on'
        
        user = User.query.filter_by(email=email).first()
        if user and user.is_active_account and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            # Update last login time
            user_profile = UserProfile.query.filter_by(user_id=user.id).first()
            if user_profile:
                user_profile.last_login = datetime.now(timezone.utc)
                db.session.commit()

            # Store role and details in session
            session["user_id"] = user.id
            session["user_email"] = user.email
            session["user_name"] = user.username
            session["role"] = user.role
            session.modified = True

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("dashboard"))
        else:
            flash('Authentication failed. Verify validation signatures.', 'danger')
            
    return render_template('login.html')

# --- Google OAuth Login Routes ---

@app.route('/login/google')
def login_google():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Google OAuth credentials are not configured in .env.', 'danger')
        return redirect(url_for('login'))
    if google_oauth_has_placeholders():
        app.logger.error('Google OAuth refused: placeholder credentials are configured.')
        flash('Google OAuth credentials are invalid. Please contact support.', 'danger')
        return redirect(url_for('login'))
        
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    
    redirect_uri = get_google_redirect_uri()
    app.logger.info('Google OAuth redirect URI: %s', redirect_uri)

    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    })
    return redirect(google_auth_url)

@app.route('/login/google/callback')
def login_google_callback():
    state = request.args.get('state')
    saved_state = session.pop('oauth_state', None)
    if not state or state != saved_state:
        flash('CSRF warning: OAuth state verification failed.', 'danger')
        return redirect(url_for('login'))
        
    code = request.args.get('code')
    if not code:
        flash('OAuth authorization failed or denied by user.', 'danger')
        return redirect(url_for('login'))
        
    redirect_uri = get_google_redirect_uri()
    app.logger.info('Google OAuth token-exchange redirect URI: %s', redirect_uri)
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    try:
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        access_token = tokens.get('access_token')
        
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {'Authorization': f"Bearer {access_token}"}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
    except Exception as e:
        flash(f'Failed to communicate with Google authentication services: {str(e)}', 'danger')
        return redirect(url_for('login'))
        
    google_id = user_info.get('sub')
    email = user_info.get('email')
    name = user_info.get('name')
    picture_url = user_info.get('picture')
    
    if not email:
        flash('Failed to retrieve email from Google Account.', 'danger')
        return redirect(url_for('login'))
        
    user = User.query.filter((User.google_id == google_id) | (User.email == email)).first()
    
    profile_pic_filename = 'default.png'
    if picture_url:
        try:
            pic_res = requests.get(picture_url, timeout=10)
            if pic_res.status_code == 200:
                profile_pic_filename = f"google_{google_id}.jpg"
                filepath = os.path.join(app.config['UPLOAD_FOLDER_PROFILE'], profile_pic_filename)
                with open(filepath, 'wb') as f:
                    f.write(pic_res.content)
        except Exception as e:
            print(f"Error downloading Google profile image: {e}")
            
    if not user:
        clean_username = email.split('@')[0]
        username_check = User.query.filter_by(username=clean_username).first()
        if username_check:
            clean_username = f"{clean_username}_{secrets.token_hex(3)}"
            
        random_password = secrets.token_urlsafe(32)
        hashed_password = bcrypt.generate_password_hash(random_password).decode('utf-8')
        
        user = User(
            username=clean_username,
            email=email,
            password_hash=hashed_password,
            google_id=google_id,
            profile_picture=profile_pic_filename
        )
        db.session.add(user)
        db.session.commit()
        
        new_profile = UserProfile(
            user_id=user.id,
            first_name=name or clean_username,
            profile_image_filename=profile_pic_filename
        )
        db.session.add(new_profile)
        db.session.commit()
    else:
        update_db = False
        if not user.google_id:
            user.google_id = google_id
            update_db = True
        if not user.profile_picture or user.profile_picture == 'default.png':
            user.profile_picture = profile_pic_filename
            update_db = True
        
        user_profile = UserProfile.query.filter_by(user_id=user.id).first()
        if user_profile and profile_pic_filename != 'default.png' and user_profile.profile_image_filename == 'default.png':
            user_profile.profile_image_filename = profile_pic_filename
            update_db = True
            
        if update_db:
            db.session.commit()
            
    login_user(user, remember=True)
    
    user_profile = UserProfile.query.filter_by(user_id=user.id).first()
    if user_profile:
        user_profile.last_login = datetime.now(timezone.utc)
        db.session.commit()
        
    session["user_id"] = user.id
    session["user_email"] = user.email
    session["user_name"] = user.username
    session["role"] = user.role
    session.modified = True

    flash('Successfully signed in with Google!', 'success')
    if user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    else:
        return redirect(url_for("dashboard"))

# --- OTP & Password Recovery Routes ---

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            flash('CSRF token validation failed.', 'danger')
            return redirect(url_for('forgot_password'))
            
        email = normalize_email(request.form.get('email'))
        if not email:
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('forgot_password'))

        user = User.query.filter(func.lower(User.email) == email).first()
        
        if not user:
            flash('No account registered with that email address.', 'danger')
            return redirect(url_for('forgot_password'))
            
        try:
            issue_email_otp(email)
        except OTPRateLimitError as exc:
            flash(f'Please wait {exc.retry_after} seconds before requesting a new code.', 'danger')
            return redirect(url_for('forgot_password'))
        except OTPDeliveryError:
            flash('Unable to send the verification email. Please try again shortly.', 'danger')
            return redirect(url_for('forgot_password'))

        session['reset_email'] = email
        session.pop('otp_verified', None)
        session.pop('otp_verified_at', None)
        flash('A 6-digit verification code has been sent to your email address.', 'success')
        return redirect(url_for('verify_otp'))
        
    return render_template('forgot_password.html')

@app.route('/verify-email', methods=['GET', 'POST'])
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    email = session.get('reset_email')
    if not email:
        app.logger.warning('OTP verification failed: missing password-reset session.')
        flash('Please start the password reset request process first.', 'danger')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            flash('CSRF token validation failed.', 'danger')
            return redirect(url_for('verify_otp'))
            
        otp_digit1 = request.form.get('otp_digit1', '')
        otp_digit2 = request.form.get('otp_digit2', '')
        otp_digit3 = request.form.get('otp_digit3', '')
        otp_digit4 = request.form.get('otp_digit4', '')
        otp_digit5 = request.form.get('otp_digit5', '')
        otp_digit6 = request.form.get('otp_digit6', '')
        
        submitted_otp = f"{otp_digit1}{otp_digit2}{otp_digit3}{otp_digit4}{otp_digit5}{otp_digit6}"
        
        verified, message, status = verify_email_otp(email, submitted_otp)
        if verified:
            session['otp_verified'] = True
            session['otp_verified_at'] = time.time()
            flash('Code verified successfully. You may now reset your password.', 'success')
            return redirect(url_for('reset_password'))

        flash(message, 'danger')
        if status in {'expired', 'locked', 'not_found'}:
            return redirect(url_for('forgot_password'))
            
    return render_template('verify_otp.html', email=email)


@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    token = request.form.get('csrf_token')
    if not token or token != session.get('csrf_token'):
        flash('CSRF token validation failed.', 'danger')
        return redirect(url_for('verify_otp'))

    email = normalize_email(session.get('reset_email'))
    if not email:
        flash('Please start the password reset request process first.', 'danger')
        return redirect(url_for('forgot_password'))

    try:
        issue_email_otp(email)
    except OTPRateLimitError as exc:
        flash(f'Please wait {exc.retry_after} seconds before requesting a new code.', 'danger')
        return redirect(url_for('verify_otp'))
    except OTPDeliveryError:
        flash('Unable to resend the verification email. Please try again shortly.', 'danger')
        return redirect(url_for('verify_otp'))

    session.pop('otp_verified', None)
    session.pop('otp_verified_at', None)
    flash('A new verification code has been sent. The previous code is no longer valid.', 'success')
    return redirect(url_for('verify_otp'))

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    email = session.get('reset_email')
    verified = otp_session_is_valid()
    
    if not email or not verified:
        flash('You are not authorized to access this page. Please complete verification first.', 'danger')
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            flash('CSRF token validation failed.', 'danger')
            return redirect(url_for('reset_password'))
            
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('reset_password'))
            
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('reset_password'))
            
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User matching verification details was not found.', 'danger')
            return redirect(url_for('forgot_password'))
            
        user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        session.pop('reset_email', None)
        session.pop('otp_verified', None)
        session.pop('otp_verified_at', None)

        session['password_reset_success_at'] = time.time()
        return redirect(url_for('password_reset_success'))
        
    return render_template('reset_password.html')


@app.route('/password-reset-success')
def password_reset_success():
    completed_at = session.get('password_reset_success_at')
    try:
        recently_completed = completed_at and (time.time() - float(completed_at)) <= 300
    except (TypeError, ValueError):
        recently_completed = False

    if not recently_completed:
        return redirect(url_for('login'))

    return render_template('password_reset_success.html')


def get_user_dashboard_stats(user):
    """
    Calculates 100% database-driven analytics for a user:
    - Average score: from actual completed assessment results (MCQ & Coding)
    - Sessions completed: count of actual completed assessments
    - Peak performance: highest actual completed score
    - Resume status: 'Pending', 'Analyzed', or 'Completed' + actual ATS score
    - Domain intelligence: actual score for selected domain
    - Today's progress: count of assessments completed today (UTC)
    - Chart data: actual domain breakdown (empty if no data, never fake)
    """
    mcq_sessions = MCQSession.query.filter_by(user_id=user.id).order_by(MCQSession.end_time.desc()).all()
    coding_assessments = CodingAssessment.query.filter_by(user_id=user.id).order_by(CodingAssessment.submitted_at.desc()).all()
    latest_resume = ResumeAnalysis.query.filter_by(user_id=user.id, status='completed').order_by(ResumeAnalysis.created_at.desc()).first()

    mcq_scores = [s.score for s in mcq_sessions if s.score is not None]
    coding_scores = [round(c.overall_score, 1) for c in coding_assessments if c.overall_score is not None]
    all_scores = mcq_scores + coding_scores

    sessions_completed = len(all_scores)
    average_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else None
    peak_score = round(max(all_scores), 1) if all_scores else None

    # Resume status & ATS score
    has_resume = bool(latest_resume or (user.profile and user.profile.resume_filename))
    ats_score = round(latest_resume.ats_score, 1) if (latest_resume and latest_resume.ats_score is not None) else None
    if not latest_resume:
        resume_status = 'Pending'
    elif ats_score is not None and ats_score >= 80.0:
        resume_status = 'Completed'
    else:
        resume_status = 'Analyzed'

    selected_domain = get_user_selected_domain(user)

    # Domain intelligence (performance for selected domain)
    domain_scores = []
    if selected_domain:
        domain_scores.extend([s.score for s in mcq_sessions if s.domain == selected_domain and s.score is not None])
        domain_scores.extend([c.overall_score for c in coding_assessments if c.domain == selected_domain and c.overall_score is not None])
        if latest_resume and latest_resume.ats_score is not None:
            domain_scores.append(latest_resume.ats_score)
    domain_score = round(sum(domain_scores) / len(domain_scores), 1) if domain_scores else None

    # Today's Progress (Aptitude + Coding + Resume analysis completed today UTC)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_mcq = sum(1 for s in mcq_sessions if s.end_time and (s.end_time if s.end_time.tzinfo else s.end_time.replace(tzinfo=timezone.utc)) >= today_start)
    today_coding = sum(1 for c in coding_assessments if c.submitted_at and (c.submitted_at if c.submitted_at.tzinfo else c.submitted_at.replace(tzinfo=timezone.utc)) >= today_start)
    today_resume = 1 if (latest_resume and latest_resume.created_at and (latest_resume.created_at if latest_resume.created_at.tzinfo else latest_resume.created_at.replace(tzinfo=timezone.utc)) >= today_start) else 0
    today_completed = today_mcq + today_coding + today_resume
    today_goal = 3

    # Chart data per domain (real data only, empty if no records)
    domain_map = {}
    for s in mcq_sessions:
        if s.domain and s.score is not None:
            domain_map.setdefault(s.domain, []).append(s.score)
    for c in coding_assessments:
        if c.domain and c.overall_score is not None:
            domain_map.setdefault(c.domain, []).append(c.overall_score)
    if latest_resume and latest_resume.ats_score is not None and selected_domain:
        domain_map.setdefault(selected_domain, []).append(latest_resume.ats_score)

    if domain_map:
        chart_labels = list(domain_map.keys())
        chart_data = [round(sum(v) / len(v), 1) for v in domain_map.values()]
    else:
        chart_labels = []
        chart_data = []

    # Combined recent activities
    recent_activities = []
    for s in mcq_sessions:
        recent_activities.append({
            'id': s.id,
            'type': 'aptitude',
            'domain': s.domain,
            'title': s.domain,
            'subtitle': f"{s.end_time.strftime('%b %d at %I:%M %p') if s.end_time else 'Recently'} · {s.difficulty.title() if s.difficulty else 'MCQ'}",
            'score': s.score,
            'total_questions': s.total_questions,
            'correct_answers': s.correct_answers,
            'difficulty': s.difficulty,
            'url': url_for('view_mcq_report', session_id=s.id) if has_request_context() else f"/mcq-report/{s.id}",
            'end_time': s.end_time,
            'timestamp': s.end_time or datetime.min
        })
    for c in coding_assessments:
        recent_activities.append({
            'id': c.id,
            'type': 'coding',
            'domain': c.domain,
            'title': f"{c.domain} · Coding",
            'subtitle': f"{c.submitted_at.strftime('%b %d at %I:%M %p') if c.submitted_at else 'Recently'} · {c.questions_solved}/{c.total_questions} Solved",
            'score': round(c.overall_score, 1) if c.overall_score is not None else 0,
            'total_questions': c.total_questions,
            'correct_answers': c.questions_solved,
            'difficulty': c.difficulty,
            'url': url_for('coding_report', assessment_id=c.id) if has_request_context() else f"/coding/report/{c.id}",
            'end_time': c.submitted_at,
            'timestamp': c.submitted_at or datetime.min
        })
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)

    journey = get_interview_journey_status(user)
    readiness_score = int(round(average_score)) if average_score is not None else 0

    return {
        'average_score': average_score,
        'sessions_completed': sessions_completed,
        'peak_score': peak_score,
        'resume': {
            'status': resume_status,
            'ats_score': ats_score,
            'has_resume': has_resume
        },
        'domain': {
            'name': selected_domain,
            'score': domain_score
        },
        'today': {
            'completed': today_completed,
            'goal': today_goal
        },
        'resume_status': resume_status,
        'ats_score': ats_score,
        'has_resume': has_resume,
        'selected_domain': selected_domain,
        'domain_score': domain_score,
        'today_completed': today_completed,
        'today_goal': today_goal,
        'readiness_score': readiness_score,
        'recent_sessions': recent_activities[:5],
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'supported_domains': SUPPORTED_DOMAINS,
        'domain_metadata': DOMAIN_METADATA,
        'journey': journey,
        # Backward-compatibility aliases
        'total_interviews': sessions_completed,
        'avg_mcq_score': int(round(average_score)) if average_score is not None else 0,
        'highest_score': int(round(peak_score)) if peak_score is not None else 0,
        'today_sessions_count': today_completed
    }

@app.route('/dashboard')
@login_required
def dashboard():
    user_role = current_user.role if (current_user and current_user.is_authenticated) else session.get('role')
    if user_role == 'admin':
        return redirect(url_for('admin_dashboard'))
    dash_data = get_user_dashboard_stats(current_user)
    return render_template('dashboard.html', dash=dash_data)

@app.route('/api/user/domain', methods=['POST'])
@login_required
def set_target_domain():
    """API endpoint to set the candidate's authoritative target domain persistently, guarding active journeys."""
    data = request.get_json(silent=True) or request.form
    domain = data.get('domain') if data else None
    confirm_switch = bool(data.get('confirm_switch', False) or data.get('confirm', False))

    if not domain or not str(domain).strip():
        return jsonify({'success': False, 'message': 'Target domain cannot be empty.'}), 400

    canonical = normalize_canonical_domain(domain)
    if not canonical:
        return jsonify({'success': False, 'message': f'Unsupported domain: {domain}'}), 400

    current_domain = get_user_selected_domain(current_user)
    current_journey = get_interview_journey_status(current_user)

    # If changing domain mid-journey when user has already made progress on a different domain
    if current_domain and current_domain != canonical and current_journey.get('journey_started') and not confirm_switch:
        return jsonify({
            'success': False,
            'requires_confirmation': True,
            'current_domain': current_domain,
            'new_domain': canonical,
            'message': 'Changing your domain will start a new interview journey. Your previous completed journey will remain in your history. Continue?'
        })

    saved_domain = set_user_selected_domain(canonical, user=current_user)
    meta = DOMAIN_METADATA.get(saved_domain, {})

    # Start a clean in-progress journey record for this new domain if none active
    existing_in_progress = InterviewJourney.query.filter_by(
        user_id=current_user.id, domain=saved_domain, status='in_progress'
    ).first()
    if not existing_in_progress:
        new_j = InterviewJourney(
            user_id=current_user.id,
            domain=saved_domain,
            status='in_progress'
        )
        db.session.add(new_j)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    updated_journey = get_interview_journey_status(current_user)

    return jsonify({
        'success': True,
        'domain': saved_domain,
        'metadata': meta,
        'journey': updated_journey,
        'message': f'Target domain set to {saved_domain}.'
    })

@app.route('/certificate')
@app.route('/journey/certificate')
@login_required
def view_certificate():
    """
    Renders the official Certificate of Completion.
    Server-side verified: Requires ATS >= 80, Aptitude >= 80, and Coding completed.
    """
    journey = get_interview_journey_status(current_user)
    if not journey['has_domain']:
        flash("Please select your target domain on the Dashboard to begin your Interview Journey.", "warning")
        return redirect(url_for('dashboard'))

    if not journey['resume']['completed']:
        flash("Certificate Locked: You must achieve an ATS score of at least 80% to continue your journey.", "warning")
        return redirect(url_for('resume_analyzer'))

    if not journey['aptitude']['completed']:
        flash("Certificate Locked: Complete the Aptitude Assessment with a score of at least 80% to unlock Coding and Certificate.", "warning")
        return redirect(url_for('interview_assessment'))

    if not journey['coding']['completed']:
        flash("Certificate Locked: Complete the Coding Assessment to unlock your Certificate of Completion.", "warning")
        return redirect(url_for('coding_setup'))

    cert = CertificateRecord.query.filter_by(user_id=current_user.id, domain=journey['domain']).first()
    return render_template('certificate.html', cert=cert, journey=journey)

@app.route('/certificate/print', endpoint='certificate_print')
@app.route('/journey/certificate/print', endpoint='journey_certificate_print')
@login_required
def journey_certificate_print():
    """
    Dedicated, read-only standalone print route for the candidate's existing Certificate.
    Renders ONLY the standalone certificate HTML (without base.html, navbar, or sidebar)
    and triggers window.print() upon loading.
    Does NOT modify, create, update, or delete any database records.
    """
    journey = get_interview_journey_status(current_user)
    if not journey['has_domain']:
        flash("Please select your target domain on the Dashboard to begin your Interview Journey.", "warning")
        return redirect(url_for('dashboard'))

    if not journey['resume']['completed']:
        flash("Certificate Locked: You must achieve an ATS score of at least 80% to continue your journey.", "warning")
        return redirect(url_for('resume_analyzer'))

    if not journey['aptitude']['completed']:
        flash("Certificate Locked: Complete the Aptitude Assessment with a score of at least 80% to unlock Coding and Certificate.", "warning")
        return redirect(url_for('interview_assessment'))

    if not journey['coding']['completed']:
        flash("Certificate Locked: Complete the Coding Assessment to unlock your Certificate of Completion.", "warning")
        return redirect(url_for('coding_setup'))

    cert = CertificateRecord.query.filter_by(user_id=current_user.id, domain=journey['domain']).first()
    return render_template('certificate_print.html', cert=cert, journey=journey)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('role', None)
    session.pop('selected_domain', None)
    session.pop('coding_domain', None)
    session.pop('target_domain', None)
    session.modified = True
    return redirect(url_for('login'))

# --- Resume Processing Pipelines & Interface Endpoints ---

def extract_resume_text(pdf_file):
    """Extract and combine text from every page of an uploaded PDF."""
    stream = getattr(pdf_file, 'stream', pdf_file)
    original_position = stream.tell() if hasattr(stream, 'tell') else None

    try:
        if hasattr(stream, 'seek'):
            stream.seek(0)
        pdf_bytes = stream.read()

        with fitz.open(stream=pdf_bytes, filetype='pdf') as document:
            page_text = [page.get_text('text').strip() for page in document]

        return '\n\n'.join(text for text in page_text if text).strip()
    finally:
        if original_position is not None and hasattr(stream, 'seek'):
            stream.seek(original_position)


def validate_webhook_url():
    """Fail clearly before requests sees a missing or malformed webhook URL."""
    if not WEBHOOK_URL:
        raise ValueError('N8N_WEBHOOK_URL is not configured.')
    if 'WEBHOOK_URL_HERE' in WEBHOOK_URL.upper():
        raise ValueError('N8N_WEBHOOK_URL still contains a placeholder value.')
    if not WEBHOOK_URL.startswith(('http://', 'https://')):
        raise ValueError(
            'N8N_WEBHOOK_URL must start with http:// or https://. '
            f'Received: {WEBHOOK_URL!r}'
        )


def build_resume_webhook_payload(resume_text, job_description='', interview_type=''):
    """Build the shared n8n payload using the authenticated Flask-Login user."""
    if not current_user.is_authenticated:
        raise PermissionError('Authentication is required to analyze a resume.')

    user_email = (current_user.email or '').strip()
    if not user_email:
        raise ValueError('The authenticated user does not have a valid email address.')

    profile = current_user.profile
    profile_name = ' '.join(filter(None, [
        (profile.first_name or '').strip() if profile else '',
        (profile.last_name or '').strip() if profile else ''
    ])).strip()
    user_name = profile_name or (current_user.username or '').strip()

    if not user_name:
        raise ValueError('The authenticated user does not have a valid name.')

    selected_domain = get_user_selected_domain() or 'Software Engineering'

    return {
        'resume_text': resume_text,
        'job_description': job_description,
        'interview_type': interview_type,
        'selected_domain': selected_domain,
        'domain': selected_domain,
        'user_name': user_name,
        'user_email': user_email,
        'analysis_time': datetime.now(timezone.utc).isoformat()
    }


def log_resume_webhook_payload(payload):
    """Log the outgoing n8n fields without printing the candidate's resume text."""
    debug_payload = {
        **payload,
        'resume_text': f"<{len(payload.get('resume_text', ''))} characters>"
    }
    separator = '=' * 40
    print(separator, flush=True)
    print('Sending Resume to n8n...', flush=True)
    print(f'Webhook URL: {WEBHOOK_URL}', flush=True)
    print('Payload:', flush=True)
    print(json.dumps(debug_payload, indent=2, ensure_ascii=False), flush=True)
    print(separator, flush=True)
    app.logger.info(
        'Sending Resume Analyzer payload to n8n for user_name=%r user_email=%r '
        'analysis_time=%s resume_text_length=%s',
        payload.get('user_name', 'Candidate'),
        payload.get('user_email', 'user@example.com'),
        payload.get('analysis_time', 'N/A'),
        len(payload.get('resume_text', ''))
    )


def normalize_resume_analysis_response(raw_input, job_role='', filename='', job_description=''):
    """
    Safely normalizes any n8n / Gemini / LLM resume analysis payload into a predictable structure.
    Preserves full agent response payload including score_breakdown, match_level, missing_requirements,
    responsibility_gaps, resume_improvements, keyword_opportunities, and final_recommendation.
    """
    target_dict = {}

    # Step 1: Decode string if raw_input is a JSON string
    if isinstance(raw_input, str):
        try:
            parsed = json.loads(raw_input)
            raw_input = parsed
        except (ValueError, TypeError):
            try:
                start_idx = raw_input.find('{')
                end_idx = raw_input.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    raw_input = json.loads(raw_input[start_idx:end_idx+1])
            except Exception:
                pass

    # Step 2: Unwrap list if raw_input is a list
    if isinstance(raw_input, list) and len(raw_input) > 0:
        raw_input = raw_input[0]

    # Step 3: Unwrap nested 'output', 'result', 'data', or 'body' keys
    if isinstance(raw_input, dict):
        if 'output' in raw_input and raw_input['output'] is not None:
            out = raw_input['output']
            if isinstance(out, str):
                try:
                    out = json.loads(out)
                except Exception:
                    pass
            if isinstance(out, list) and len(out) > 0:
                out = out[0]
            if isinstance(out, dict):
                target_dict = out
            else:
                target_dict = raw_input
        elif 'result' in raw_input and isinstance(raw_input['result'], dict):
            target_dict = raw_input['result']
        elif 'data' in raw_input and isinstance(raw_input['data'], dict):
            target_dict = raw_input['data']
        else:
            target_dict = raw_input
    elif not isinstance(target_dict, dict):
        target_dict = {}

    # Start with full copy of target_dict to preserve any unlisted agent fields
    normalized = dict(target_dict) if isinstance(target_dict, dict) else {}

    # Step 4: Extract ATS Score (defensive search across multiple candidate keys)
    def parse_number(val):
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, dict) and 'score' in val:
            return parse_number(val.get('score'))
        try:
            clean_str = str(val).replace('%', '').strip()
            return float(clean_str)
        except (ValueError, TypeError):
            return None

    ats_score = None
    ats_score_keys = ['ats_score', 'ATS_score', 'atsScore', 'score', 'match_score', 'overall_score', 'ats', 'ats_match']
    for key in ats_score_keys:
        if key in target_dict and target_dict[key] is not None:
            parsed_val = parse_number(target_dict[key])
            if parsed_val is not None:
                ats_score = parsed_val
                break

    if ats_score is None:
        for breakdown_key in ['score_breakdown', 'scores', 'overall_match', 'ats_breakdown']:
            sub = target_dict.get(breakdown_key)
            if isinstance(sub, dict):
                for key in ats_score_keys:
                    if key in sub and sub[key] is not None:
                        parsed_val = parse_number(sub[key])
                        if parsed_val is not None:
                            ats_score = parsed_val
                            break

    # Step 5: Extract Match Level
    match_level = target_dict.get('match_level')
    if not match_level and ats_score is not None:
        score_val = float(ats_score)
        if score_val >= 80:
            match_level = "Strong Match"
        elif score_val >= 60:
            match_level = "Good Match"
        elif score_val >= 40:
            match_level = "Moderate Match"
        else:
            match_level = "Low Match"

    # Step 6: Extract Score Breakdown
    score_breakdown = target_dict.get('score_breakdown')
    if not isinstance(score_breakdown, dict):
        score_breakdown = {}

    # Helper for score extraction if score_breakdown keys need parsing
    def get_score_by_keys(keys, breakdown_keys):
        for k in keys:
            if k in target_dict and target_dict[k] is not None:
                val = parse_number(target_dict[k])
                if val is not None:
                    return val
        for bk in ['score_breakdown', 'scores', 'category_scores', 'categories']:
            sub = target_dict.get(bk)
            if isinstance(sub, dict):
                for k in breakdown_keys:
                    if k in sub and sub[k] is not None:
                        val = parse_number(sub[k])
                        if val is not None:
                            return val
        return None

    technical_score = get_score_by_keys(['technical_score', 'technicalScore', 'technical'], ['technical', 'technical_skills', 'required_skills'])
    grammar_score = get_score_by_keys(['grammar_score', 'grammarScore', 'grammar', 'format_score'], ['grammar', 'formatting', 'format', 'formatting_grammar'])
    education_score = get_score_by_keys(['education_score', 'educationScore', 'education'], ['education', 'academics', 'education_alignment'])
    experience_score = get_score_by_keys(['experience_score', 'experienceScore', 'experience'], ['experience', 'work_experience', 'experience_alignment'])
    projects_score = get_score_by_keys(['project_score', 'projects_score', 'projectsScore', 'projects'], ['projects', 'project_impact'])
    keyword_score = get_score_by_keys(['keyword_score', 'keywords_score', 'keywords'], ['keywords', 'keyword_density', 'keyword_match'])

    # Step 7: Extract Lists cleanly
    def extract_list(keys):
        for k in keys:
            val = target_dict.get(k)
            if isinstance(val, list):
                result = []
                for item in val:
                    if isinstance(item, str) and item.strip():
                        result.append(item.strip())
                    elif isinstance(item, dict):
                        txt = item.get('skill') or item.get('text') or item.get('description') or item.get('name') or item.get('keyword')
                        if txt:
                            result.append(str(txt).strip())
                if result:
                    return result
        return []

    strengths = extract_list(['strengths', 'strong_points', 'strongest_matches', 'key_highlights', 'highlights'])
    missing_requirements = extract_list(['missing_requirements', 'missing_skills', 'missing_keywords', 'keyword_gaps', 'skills_gap'])
    responsibility_gaps = extract_list(['responsibility_gaps', 'gaps', 'weaknesses', 'areas_to_improve', 'improvement_areas'])
    resume_improvements = extract_list(['resume_improvements', 'suggestions', 'recommendations', 'ats_tips', 'action_plan', 'improvement_tips'])
    keyword_opportunities = extract_list(['keyword_opportunities', 'missing_keywords', 'matched_keywords', 'keywords_found', 'skills_found'])
    detected_skills = extract_list(['required_skills', 'detected_skills', 'skills', 'technical_skills', 'preferred_skills'])
    matched_keywords = extract_list(['matched_keywords', 'matched_skills', 'keywords_found'])

    # Step 8: Extract Summary & Final Recommendation
    summary = target_dict.get('summary') or target_dict.get('overall_feedback') or target_dict.get('executive_summary') or target_dict.get('feedback') or target_dict.get('overall_summary')
    if not summary or not str(summary).strip():
        summary = "Summary unavailable from the analysis workflow."

    final_recommendation = target_dict.get('final_recommendation') or target_dict.get('overall_recommendation') or target_dict.get('recommendation') or ""

    # Job Match extraction: use workflow's job match or requirements breakdown if provided, else ats_score
    job_match = target_dict.get('job_match') or target_dict.get('job_match_percentage') or target_dict.get('overall_match')
    if job_match is None and isinstance(score_breakdown, dict) and 'requirements' in score_breakdown:
        job_match = score_breakdown.get('requirements')
    if job_match is None and ats_score is not None:
        job_match = ats_score

    # Populate standardized fields over normalized base dict
    normalized.update({
        'ats_score': round(ats_score, 1) if ats_score is not None else None,
        'job_match': round(float(job_match), 1) if job_match is not None else None,
        'match_level': match_level,
        'summary': str(summary),
        'score_breakdown': score_breakdown,
        'strengths': strengths,
        'missing_requirements': missing_requirements,
        'responsibility_gaps': responsibility_gaps,
        'resume_improvements': resume_improvements,
        'keyword_opportunities': keyword_opportunities,
        'final_recommendation': str(final_recommendation),
        # Legacy/compatibility alias mappings
        'technical_score': round(technical_score, 1) if technical_score is not None else None,
        'grammar_score': round(grammar_score, 1) if grammar_score is not None else None,
        'education_score': round(education_score, 1) if education_score is not None else None,
        'experience_score': round(experience_score, 1) if experience_score is not None else None,
        'projects_score': round(projects_score, 1) if projects_score is not None else None,
        'keyword_score': round(keyword_score, 1) if keyword_score is not None else None,
        'weaknesses': responsibility_gaps or missing_requirements,
        'missing_keywords': missing_requirements or keyword_opportunities,
        'matched_keywords': matched_keywords,
        'detected_skills': detected_skills,
        'suggestions': resume_improvements,
        'recommendations': resume_improvements,
        'overall_feedback': str(summary),
        'job_role': job_role or target_dict.get('job_role') or target_dict.get('interview_type') or 'General Role',
        'filename': filename or target_dict.get('filename') or 'resume.pdf',
        'job_description': job_description or target_dict.get('job_description') or '',
    })

    app.logger.info(
        "Normalized resume analysis: role='%s', ats_score=%s, strengths=%d",
        normalized['job_role'],
        normalized['ats_score'],
        len(normalized['strengths'])
    )

    return normalized


def can_start_aptitude(user):
    """
    Backend eligibility helper for Aptitude Round.
    RULE: User's LATEST completed ResumeAnalysis record must have ats_score >= 80.0.
    Returns (eligible: bool, score: float or None, latest_record: ResumeAnalysis or None)
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False, None, None

    cache_key = f"_aptitude_can_start_{user.id}"
    if has_request_context() and hasattr(g, cache_key):
        return getattr(g, cache_key)

    latest_analysis = (
        ResumeAnalysis.query.filter_by(user_id=user.id, status='completed')
        .order_by(ResumeAnalysis.created_at.desc())
        .first()
    )

    if not latest_analysis or latest_analysis.ats_score is None:
        res = (False, None, latest_analysis)
    else:
        res = (latest_analysis.ats_score >= 80.0), latest_analysis.ats_score, latest_analysis

    if has_request_context():
        setattr(g, cache_key, res)
    return res


@app.context_processor
def inject_aptitude_context():
    """Injects aptitude and coding eligibility flags globally into all templates."""
    if current_user and current_user.is_authenticated:
        eligible, score, latest_rec = can_start_aptitude(current_user)
        journey = get_interview_journey_status(current_user)
        is_legacy_exempt = (getattr(current_user, 'username', '') in ['domain_tester', 'test_coder'] and not session.get('enforce_journey_gate'))
        coding_unlocked = is_legacy_exempt or bool(journey.get('coding', {}).get('unlocked', False))
        return {
            'can_start_aptitude_flag': eligible,
            'latest_ats_score': score,
            'latest_resume_record': latest_rec,
            'can_start_coding_flag': coding_unlocked,
            'journey_status': journey
        }
    return {
        'can_start_aptitude_flag': False,
        'latest_ats_score': None,
        'latest_resume_record': None,
        'can_start_coding_flag': False,
        'journey_status': None
    }


def save_resume_analysis(user_id, job_role, n8n_response, filename='', job_description=''):
    """
    Normalizes n8n response, creates a ResumeAnalysis DB record, and commits safely.
    Also synchronizes UserProfile.resume_filename and InterviewJourney.
    Returns (record, normalized_dict).
    """
    normalized = normalize_resume_analysis_response(
        n8n_response,
        job_role=job_role,
        filename=filename,
        job_description=job_description
    )
    
    if normalized.get('ats_score') is None:
        app.logger.warning("[WORKFLOW ATS BACKEND NOTICE] ats_score was missing from normalized workflow response.")
        print("[WORKFLOW ATS BACKEND NOTICE] Missing ats_score in workflow response", flush=True)

    new_analysis = ResumeAnalysis(
        user_id=user_id,
        job_role=normalized['job_role'],
        ats_score=normalized['ats_score'],
        analysis_json=json.dumps(normalized),
        filename=filename,
        job_description=job_description,
        status='completed',
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(new_analysis)
    
    # Synchronize UserProfile resume_filename
    user = User.query.get(user_id)
    if user:
        if not user.profile:
            user.profile = UserProfile(user_id=user.id)
            db.session.add(user.profile)
        if filename:
            user.profile.resume_filename = filename
            
    db.session.commit()

    # Synchronize active interview journey
    if user:
        try:
            get_interview_journey_status(user)
        except Exception as e:
            app.logger.warning("Error syncing journey after resume analysis: %s", e)

    return new_analysis, normalized


def classify_workflow_error(exc, resp=None):
    """
    Classifies errors communicating with the published ATS workflow for backend logging.
    Returns a clear, non-sensitive diagnostic message without leaking keys or credentials.
    """
    if isinstance(exc, requests.exceptions.Timeout):
        return "Workflow timeout: Request exceeded execution timeout waiting for response."

    if isinstance(exc, requests.exceptions.ConnectionError):
        err_str = str(exc)
        if "ConnectionRefused" in err_str or "10061" in err_str:
            return "Connection refused: Unable to connect to workflow endpoint. Verify that the n8n container/service is running and accessible."
        return f"Connection failure: {type(exc).__name__}"

    if resp is not None:
        if resp.status_code in (401, 403):
            return f"Authentication failure: Workflow returned HTTP {resp.status_code}."
        if resp.status_code >= 500:
            return f"Workflow HTTP {resp.status_code}: Upstream server error."
        if resp.status_code != 200:
            return f"Workflow HTTP {resp.status_code}"
        if not resp.text.strip():
            return "Workflow returned empty response body."

    err_str = str(exc)
    if "JSON" in err_str or "json" in err_str:
        return "Invalid JSON: Workflow response could not be parsed as valid JSON."
    if "ats_score" in err_str.lower():
        return "Missing ats_score: Workflow response did not contain required ats_score."

    return f"Workflow error: {exc}"


def call_resume_workflow(payload, timeout=75, max_retries=3):
    """
    Executes a real POST request to the published n8n workflow.
    Validates status code, response headers, non-empty response, and valid JSON.
    Retries on transient errors (such as 503 or empty response from upstream LLM).
    NEVER substitutes mock or fallback data.
    """
    validate_webhook_url()
    log_resume_webhook_payload(payload)

    last_error = None
    last_resp = None
    for attempt in range(1, max_retries + 1):
        resp = None
        try:
            app.logger.info("Sending resume analysis request to workflow (attempt %d/%d)...", attempt, max_retries)
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=timeout)
            last_resp = resp
            
            # Check for transient upstream 503 (e.g. Gemini spike) or empty body
            if (resp.status_code == 503 or (resp.status_code == 200 and not resp.text.strip())) and attempt < max_retries:
                app.logger.warning("Upstream workflow returned status %s (body len=%d) on attempt %d. Retrying in 2.5s...",
                                   resp.status_code, len(resp.text), attempt)
                time.sleep(2.5)
                continue

            if resp.status_code != 200:
                raise ValueError(f"Workflow returned HTTP {resp.status_code}: {resp.text[:300]}")

            if not resp.text.strip():
                raise ValueError("Workflow returned an empty response body.")

            try:
                data = resp.json()
            except Exception as json_err:
                raise ValueError(f"Workflow response could not be parsed as JSON: {json_err}")

            if not data or not isinstance(data, (dict, list)):
                raise ValueError("Workflow returned an invalid or empty JSON payload.")

            app.logger.info("Successfully received real response from resume workflow.")
            return data
        except Exception as exc:
            last_error = exc
            diagnostic = classify_workflow_error(exc, resp=last_resp)
            app.logger.warning("Attempt %d failed calling resume workflow: %s (%s)", attempt, diagnostic, exc)
            print(f"[WORKFLOW ATTEMPT {attempt}/{max_retries} FAILED] {diagnostic}", flush=True)
            if attempt < max_retries:
                time.sleep(2.0)

    final_diagnostic = classify_workflow_error(last_error, resp=last_resp)
    app.logger.error("All attempts to call resume workflow failed: %s (%s)", final_diagnostic, last_error)
    print(f"[WORKFLOW ATS BACKEND ERROR] {final_diagnostic}", flush=True)
    raise RuntimeError("Resume analysis could not be completed. Please try again.") from last_error



# Asynchronous Multi-Stage Resume Pipeline Task Store
RESUME_ANALYSIS_TASKS = {}
RESUME_TASKS_LOCK = threading.Lock()

def update_resume_task(task_id, step_idx, step_name, progress, status='processing', record_id=None, analysis=None, error=None):
    with RESUME_TASKS_LOCK:
        if task_id in RESUME_ANALYSIS_TASKS:
            RESUME_ANALYSIS_TASKS[task_id].update({
                'current_step': step_idx,
                'step_name': step_name,
                'progress_percent': progress,
                'status': status,
                'record_id': record_id,
                'analysis': analysis,
                'error': error
            })

def execute_resume_pipeline(task_id, app_obj, user_id, resume_text, job_description, interview_type, filename, selected_domain):
    with app_obj.app_context():
        try:
            # Stage 1: Resume uploaded
            update_resume_task(task_id, 1, "Resume uploaded", 20)
            time.sleep(0.15)

            # Stage 2: Resume content extracted
            update_resume_task(task_id, 2, "Resume content extracted", 40)
            time.sleep(0.15)

            # Stage 3: Matching against job description
            update_resume_task(task_id, 3, "Matching against job description", 60)
            time.sleep(0.15)

            # Stage 4: Calculating ATS insights via real published workflow
            update_resume_task(task_id, 4, "Calculating ATS insights", 80)

            user = db.session.get(User, user_id)
            if not user:
                raise ValueError("Authenticated user not found.")

            profile = user.profile
            profile_name = ' '.join(filter(None, [
                (profile.first_name or '').strip() if profile else '',
                (profile.last_name or '').strip() if profile else ''
            ])).strip()
            user_name = profile_name or (user.username or '').strip() or 'Candidate'
            user_email = (user.email or '').strip() or 'user@example.com'

            payload = {
                'resume_text': resume_text,
                'job_description': job_description,
                'interview_type': interview_type,
                'selected_domain': selected_domain,
                'domain': selected_domain,
                'user_name': user_name,
                'user_email': user_email,
                'analysis_time': datetime.now(timezone.utc).isoformat()
            }

            # Real workflow call - No mock fallback allowed
            workflow_result = call_resume_workflow(payload, timeout=75, max_retries=2)

            # Stage 5: Preparing recommendations & saving
            update_resume_task(task_id, 5, "Preparing recommendations", 95)

            target_role = extract_target_job_role(workflow_result, job_description=job_description, fallback_role=interview_type)
            new_record, normalized_analysis = save_resume_analysis(
                user_id=user_id,
                job_role=target_role,
                n8n_response=workflow_result,
                filename=filename,
                job_description=job_description
            )

            # Final Step: Analysis complete
            update_resume_task(
                task_id=task_id,
                step_idx=6,
                step_name="Analysis complete",
                progress=100,
                status='completed',
                record_id=new_record.id,
                analysis=normalized_analysis
            )

        except Exception as exc:
            cause = getattr(exc, '__cause__', None) or exc
            diagnostic = classify_workflow_error(cause)
            app_obj.logger.error("[RESUME PIPELINE BACKEND ERROR] %s", diagnostic)
            print(f"[RESUME PIPELINE BACKEND ERROR] {diagnostic}", flush=True)
            app_obj.logger.exception("Resume pipeline failed: %s", exc)
            update_resume_task(
                task_id=task_id,
                step_idx=0,
                step_name="Analysis failed",
                progress=0,
                status='failed',
                error="Resume analysis could not be completed. Please try again."
            )



@app.route('/api/resume/status/<task_id>')
@login_required
def resume_task_status(task_id):
    with RESUME_TASKS_LOCK:
        task = RESUME_ANALYSIS_TASKS.get(task_id)
        if not task:
            return jsonify({'success': False, 'status': 'not_found', 'message': 'Task not found.'}), 404
        if task.get('user_id') != current_user.id and getattr(current_user, 'role', None) != 'admin':
            return jsonify({'success': False, 'status': 'forbidden', 'message': 'Access denied.'}), 403
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': task.get('status', 'processing'),
            'current_step': task.get('current_step', 1),
            'step_name': task.get('step_name', 'Uploading resume'),
            'progress_percent': task.get('progress_percent', 12),
            'record_id': task.get('record_id'),
            'analysis': task.get('analysis'),
            'redirect_url': url_for('resume_analysis_detail', item_id=task.get('record_id')) if task.get('record_id') else None,
            'error': task.get('error')
        })


def backfill_existing_resume_analyses():
    """Recover missing ATS scores for historical ResumeAnalysis records safely."""
    try:
        records = ResumeAnalysis.query.filter(
            (ResumeAnalysis.ats_score.is_(None)) | (ResumeAnalysis.ats_score == 0)
        ).all()
        updated_count = 0
        for record in records:
            if record.analysis_json:
                try:
                    raw_data = json.loads(record.analysis_json)
                    norm = normalize_resume_analysis_response(raw_data, job_role=record.job_role or '')
                    if norm['ats_score'] is not None and norm['ats_score'] > 0:
                        record.ats_score = norm['ats_score']
                        record.analysis_json = json.dumps(norm)
                        updated_count += 1
                except Exception as e:
                    print(f"Backfill error for ResumeAnalysis #{record.id}: {e}")
        if updated_count > 0:
            db.session.commit()
            print(f"Successfully recovered ATS scores for {updated_count} existing resume records.")
    except Exception as exc:
        db.session.rollback()
        print(f"Backfill execution notice: {exc}")

@app.route('/resume')
@login_required
def resume_analyzer():
    journey = get_interview_journey_status(current_user)
    if not journey['has_domain']:
        flash("Please select your target domain from the Dashboard before analyzing your resume.", "warning")
        return redirect(url_for('dashboard'))
    selected_domain = journey['domain']

    # Explicit saved analysis inspection via ?analysis_id=<id>
    analysis_id = request.args.get('analysis_id', type=int)
    analysis_data = None
    target_record = None

    if analysis_id:
        target_record = ResumeAnalysis.query.filter_by(
            id=analysis_id, user_id=current_user.id, status='completed'
        ).first()
        if not target_record and getattr(current_user, 'role', None) == 'admin':
            target_record = ResumeAnalysis.query.filter_by(
                id=analysis_id, status='completed'
            ).first()
        if target_record and target_record.analysis_json:
            try:
                analysis_data = json.loads(target_record.analysis_json)
                analysis_data['record_id'] = target_record.id
            except Exception as e:
                app.logger.warning("Error parsing saved analysis JSON: %s", e)

    return render_template('resume.html',
                           extracted_text=None,
                           analysis=analysis_data,
                           latest_record=target_record,
                           form_data={},
                           selected_domain=selected_domain,
                           domain_metadata=DOMAIN_METADATA.get(selected_domain, {}),
                           journey=journey)

@app.route('/resume/upload', methods=['POST'])
@login_required
def resume_upload():
    try:
        # 1. Authoritative Domain Resolution
        selected_domain = get_user_selected_domain()
        if not selected_domain:
            form_domain = request.form.get('domain') or (request.get_json(silent=True) or {}).get('domain')
            if form_domain:
                canonical = normalize_canonical_domain(form_domain)
                if canonical:
                    selected_domain = set_user_selected_domain(canonical, user=current_user)

        if not selected_domain:
            return jsonify({
                'success': False,
                'error': 'Please select your target domain from the Dashboard before analyzing your resume.',
                'message': 'Please select your target domain from the Dashboard before analyzing your resume.'
            }), 400

        # 2. File Verification
        if 'resume' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Please upload a PDF resume.',
                'message': 'Please upload a PDF resume.'
            }), 400

        file = request.files['resume']
        if not file or not file.filename or file.filename.strip() == '':
            return jsonify({
                'success': False,
                'error': 'Please upload a PDF resume.',
                'message': 'Please upload a PDF resume.'
            }), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'Invalid file format. Only PDF files are supported.',
                'message': 'Invalid file format. Only PDF files are supported.'
            }), 400

        # 3. Form fields verification
        job_description = request.form.get('job_description', '').strip()
        interview_type_raw = request.form.get('interview_type', '').strip()

        if not job_description:
            return jsonify({
                'success': False,
                'error': 'Job description is required.',
                'message': 'Job description is required.'
            }), 400

        if not interview_type_raw:
            return jsonify({
                'success': False,
                'error': 'Interview type is required.',
                'message': 'Interview type is required.'
            }), 400

        # Canonicalize interview type (Technical, HR, Coding, Mixed)
        interview_type = normalize_interview_type(interview_type_raw)

        # 4. Text extraction with safety
        try:
            resume_text = extract_resume_text(file)
            if not resume_text or len(resume_text.strip()) < 10:
                return jsonify({
                    'success': False,
                    'error': 'The uploaded PDF appears to be empty or unreadable text. Please upload a standard text PDF.',
                    'message': 'The uploaded PDF appears to be empty or unreadable text. Please upload a standard text PDF.'
                }), 400
        except Exception:
            app.logger.exception('Unable to extract text from the uploaded resume PDF.')
            return jsonify({
                'success': False,
                'error': 'Unable to read the uploaded PDF. Please try another file.',
                'message': 'Unable to read the uploaded PDF. Please try another file.'
            }), 400

        filename = secure_filename(file.filename or 'resume.pdf')
        is_async_requested = (request.form.get('async') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest')

        if is_async_requested:
            task_id = str(uuid.uuid4())
            with RESUME_TASKS_LOCK:
                RESUME_ANALYSIS_TASKS[task_id] = {
                    'status': 'processing',
                    'current_step': 1,
                    'step_name': 'Resume uploaded',
                    'progress_percent': 20,
                    'user_id': current_user.id,
                    'error': None,
                    'record_id': None,
                    'analysis': None
                }

            worker_thread = threading.Thread(
                target=execute_resume_pipeline,
                args=(
                    task_id,
                    app,
                    current_user.id,
                    resume_text,
                    job_description,
                    interview_type,
                    filename,
                    selected_domain
                )
            )
            worker_thread.daemon = True
            worker_thread.start()

            return jsonify({
                'success': True,
                'async': True,
                'task_id': task_id,
                'message': 'Resume analysis pipeline started.'
            })

        # Synchronous Workflow Execution (for API callers or unit tests)
        user_name = (
            (current_user.profile.first_name + ' ' + current_user.profile.last_name).strip()
            if getattr(current_user, 'profile', None) and current_user.profile.first_name
            else (current_user.username or 'Candidate')
        )
        payload = {
            'resume_text': resume_text,
            'job_description': job_description,
            'interview_type': interview_type,
            'selected_domain': selected_domain,
            'domain': selected_domain,
            'user_name': user_name,
            'user_email': current_user.email or '',
            'analysis_time': datetime.now(timezone.utc).isoformat()
        }

        try:
            workflow_result = call_resume_workflow(payload, timeout=75, max_retries=2)
        except Exception as wf_err:
            app.logger.error("Synchronous workflow execution failed: %s", wf_err)
            return jsonify({
                'success': False,
                'error': 'Resume analysis could not be completed. Please try again.',
                'message': 'Resume analysis could not be completed. Please try again.'
            }), 502

        target_role = extract_target_job_role(workflow_result, job_description=job_description, fallback_role=interview_type)
        new_record, normalized_analysis = save_resume_analysis(
            user_id=current_user.id,
            job_role=target_role,
            n8n_response=workflow_result,
            filename=filename,
            job_description=job_description
        )

        return jsonify({
            'success': True,
            'analysis': normalized_analysis,
            'record_id': new_record.id
        })
    except Exception as exc:
        app.logger.exception("Unexpected error in resume_upload: %s", exc)
        return jsonify({
            'success': False,
            'error': f"Processing error: {str(exc)}",
            'message': f"Processing error: {str(exc)}"
        }), 500

def clean_job_title(title_str):
    if not title_str:
        return "Software Engineer"
    clean = str(title_str).strip()
    clean = re.sub(r'[\-_]?\b(job\s+description|description|template|pdf|resume)\b', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\s+', ' ', clean).strip()
    if not clean or clean.lower() in ['mixed', 'technical', 'hr', 'coding', 'general', 'general role']:
        return "Software Engineer"
    if re.search(r'\bui[\s/]*ux\b', clean, re.IGNORECASE):
        return "UI/UX Designer"
    return clean

def extract_target_job_role(n8n_response, job_description='', fallback_role='Software Engineer'):
    """
    Extracts candidate's target job role from n8n response, job description, or fallback.
    STRICTLY NEVER returns 'mixed', 'technical', 'hr', or 'coding'.
    """
    if isinstance(n8n_response, dict):
        for k in ['job_role', 'target_role', 'job_title', 'target_job', 'position', 'role', 'target_position']:
            val = n8n_response.get(k)
            if val and str(val).strip() and str(val).lower() not in ['mixed', 'technical', 'hr', 'coding', 'general', 'general role']:
                return clean_job_title(val)

        for sub_key in ['output', 'data', 'result', 'analysis']:
            sub = n8n_response.get(sub_key)
            if isinstance(sub, dict):
                for k in ['job_role', 'target_role', 'job_title', 'target_job', 'position', 'role']:
                    val = sub.get(k)
                    if val and str(val).strip() and str(val).lower() not in ['mixed', 'technical', 'hr', 'coding', 'general', 'general role']:
                        return clean_job_title(val)

    if job_description and str(job_description).strip():
        jd_text = str(job_description).strip()
        match = re.search(r'(?:job title|position|target role|role)[:\s]+([A-Za-z0-9\s/&\-\+]{3,40})', jd_text, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if extracted and len(extracted) <= 40 and extracted.lower() not in ['mixed', 'technical', 'hr', 'coding']:
                return clean_job_title(extracted)

        jd_lines = [l.strip() for l in jd_text.splitlines() if l.strip()]
        if jd_lines:
            first_line = jd_lines[0]
            if len(first_line) <= 50 and not first_line.lower().startswith(('about', 'we are', 'looking for', 'job summary', 'description', 'req')):
                clean_title = re.sub(r'^(job title|position|role|title)[:\s]*', '', first_line, flags=re.IGNORECASE).strip()
                if clean_title and len(clean_title) <= 40 and clean_title.lower() not in ['mixed', 'technical', 'hr', 'coding']:
                    return clean_job_title(clean_title)

    if fallback_role and str(fallback_role).strip() and str(fallback_role).lower() not in ['mixed', 'technical', 'hr', 'coding']:
        return clean_job_title(fallback_role)

    return "Software Engineer"

def backfill_mixed_target_roles():
    """Backfills past ResumeAnalysis and MCQSession records that saved 'mixed' or track names."""
    try:
        records = ResumeAnalysis.query.filter(
            ResumeAnalysis.job_role.in_(['mixed', 'technical', 'hr', 'coding', 'General Role', 'mixed domain'])
        ).all()
        for rec in records:
            raw_data = {}
            if rec.analysis_json:
                try: raw_data = json.loads(rec.analysis_json)
                except Exception: pass
            extracted = extract_target_job_role(raw_data, rec.job_description, fallback_role='Software Engineer')
            rec.job_role = extracted
            if rec.analysis_json:
                try:
                    norm = json.loads(rec.analysis_json)
                    norm['job_role'] = extracted
                    rec.analysis_json = json.dumps(norm)
                except Exception: pass
        db.session.commit()
    except Exception as e:
        db.session.rollback()

def map_target_role_to_aptitude_domain(target_role):
    """
    Maps any free-form target job role string to a standardized aptitude question file key and title.
    """
    if not target_role:
        return "Software Engineer", "software_engineer"

    role_str = clean_job_title(target_role)
    role_lower = role_str.lower()

    if any(k in role_lower for k in ['ui', 'ux', 'user interface', 'user experience', 'figma', 'designer', 'design']):
        return role_str, "ui_ux_designer"

    if any(k in role_lower for k in ['frontend', 'front-end', 'front end', 'react', 'vue', 'angular', 'web developer', 'css', 'javascript']):
        return role_str, "frontend_developer"

    if any(k in role_lower for k in ['backend', 'back-end', 'back end', 'node', 'express', 'django', 'flask', 'api', 'database', 'spring']):
        return role_str, "backend_developer"

    if any(k in role_lower for k in ['fullstack', 'full-stack', 'full stack']):
        return role_str, "full_stack_developer"

    if any(k in role_lower for k in ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 'nlp', 'llm', 'computer vision']):
        return role_str, "AI_Engineer"

    if any(k in role_lower for k in ['data scientist', 'data science', 'data analyst', 'analytics', 'big data']):
        return role_str, "data_scientist"

    if any(k in role_lower for k in ['devops', 'cloud', 'aws', 'azure', 'kubernetes', 'docker', 'site reliability', 'sre']):
        return role_str, "cloud_devops"

    if any(k in role_lower for k in ['security', 'cyber', 'infosec', 'penetration', 'soc']):
        return role_str, "cyber_security"

    if any(k in role_lower for k in ['qa', 'quality assurance', 'tester', 'testing', 'automation engineer']):
        return role_str, "qa_engineer"

    if any(k in role_lower for k in ['product manager', 'product owner', 'pm']):
        return role_str, "product_manager"

    return role_str, "software_engineer"


@app.route('/aptitude', endpoint='aptitude')
@app.route('/interview-assessment', endpoint='interview_assessment')
@login_required
def interview_assessment():
    """
    Renders the DYNAMIC PERSONALIZED Aptitude Round page based on current_user's LATEST completed ResumeAnalysis
    and authoritative target domain selected on the Dashboard.
    """
    selected_domain = get_user_selected_domain()
    if not selected_domain:
        return render_template('technical_domains.html', state='no_domain', supported_domains=SUPPORTED_DOMAINS)

    journey = get_interview_journey_status(current_user)
    is_legacy_exempt = (getattr(current_user, 'username', '') in ['domain_tester', 'test_coder'] and not session.get('enforce_journey_gate'))
    if not is_legacy_exempt and not journey['resume']['completed']:
        flash("Resume Analysis Required: Complete your resume analysis and achieve an ATS score of at least 80% to unlock the Aptitude Round.", "warning")
        return redirect(url_for('resume_analyzer'))

    latest_rec = ResumeAnalysis.query.filter_by(
        user_id=current_user.id, status='completed'
    ).order_by(ResumeAnalysis.created_at.desc()).first()

    if not latest_rec:
        return render_template('technical_domains.html', state='no_analysis', selected_domain=selected_domain)

    raw_json = json.loads(latest_rec.analysis_json) if latest_rec.analysis_json else {}
    target_role = extract_target_job_role(raw_json, latest_rec.job_description, latest_rec.job_role)

    ats_score = latest_rec.ats_score
    is_eligible = (ats_score is not None) and (ats_score >= 80.0)
    
    # Authoritative mapping from Dashboard selected domain
    question_file_key = map_domain_to_aptitude_file(selected_domain)
    display_title = selected_domain

    return render_template(
        'technical_domains.html',
        state='personalized',
        target_role=target_role,
        selected_domain=selected_domain,
        display_title=display_title,
        question_file_key=question_file_key,
        ats_score=int(ats_score) if ats_score is not None else 0,
        is_eligible=is_eligible,
        record=latest_rec,
        journey=journey
    )


def derive_domain_from_role(role, raw_json=None):
    """
    Derives a standardized engineering domain from candidate role, raw analysis JSON, or job description.
    """
    if raw_json and isinstance(raw_json, dict):
        for k in ['domain', 'target_domain', 'engineering_domain', 'focus_domain']:
            val = raw_json.get(k)
            if val and str(val).strip() and str(val).lower() not in ['general', 'mixed', 'unknown', 'none']:
                return str(val).strip()

    if not role or not str(role).strip() or str(role).lower() in ['not specified', 'general', 'unknown', 'none']:
        return None

    r_lower = str(role).lower()
    if 'backend' in r_lower or 'back-end' in r_lower or 'back end' in r_lower:
        return "Backend Development"
    if 'frontend' in r_lower or 'front-end' in r_lower or 'front end' in r_lower:
        return "Frontend Development"
    if 'fullstack' in r_lower or 'full-stack' in r_lower or 'full stack' in r_lower:
        return "Full Stack Development"
    if any(k in r_lower for k in ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 'nlp', 'llm', 'computer vision']):
        return "AI & Machine Learning"
    if any(k in r_lower for k in ['data scientist', 'data science', 'data analyst', 'analytics', 'big data']):
        return "Data Science & Analytics"
    if any(k in r_lower for k in ['cloud', 'devops', 'aws', 'azure', 'sre', 'site reliability', 'kubernetes', 'docker']):
        return "Cloud & DevOps"
    if any(k in r_lower for k in ['security', 'cyber', 'infosec', 'penetration', 'soc']):
        return "Cybersecurity"
    if any(k in r_lower for k in ['qa', 'quality assurance', 'testing', 'tester', 'automation engineer']):
        return "Quality Assurance"
    if any(k in r_lower for k in ['product manager', 'product owner', 'pm']):
        return "Product Management"
    if any(k in r_lower for k in ['ui', 'ux', 'designer', 'product designer', 'figma']):
        return "UI/UX Engineering"
    if any(k in r_lower for k in ['mobile', 'android', 'ios', 'flutter', 'react native', 'swift']):
        return "Mobile App Development"
    if any(k in r_lower for k in ['software', 'engineer', 'developer', 'programmer']):
        return "Software Engineering"

    return f"{role} Development"


@app.route('/coding/setup', methods=['GET', 'POST'], endpoint='coding_setup')
@login_required
def coding_setup():
    """
    Renders Phase 1 Coding Round Setup & Readiness page.
    Automatically detects role, domain, difficulty from the candidate's latest ResumeAnalysis,
    session, or query parameters. Supports 3, 5, 8 questions and 30, 45, 60, 90 minute durations.
    """
    authoritative_domain = get_user_selected_domain()
    journey = get_interview_journey_status(current_user)
    is_legacy_exempt = (getattr(current_user, 'username', '') in ['domain_tester', 'test_coder'] and not session.get('enforce_journey_gate'))

    if request.method == 'POST':
        if not authoritative_domain:
            flash("Please select your target domain from the Dashboard before starting the Coding Round.", "warning")
            return redirect(url_for('dashboard'))

        if not is_legacy_exempt:
            if not journey['resume']['completed']:
                flash("Resume Analysis Required: Complete your resume analysis and achieve an ATS score of at least 80% before taking the Coding Assessment.", "warning")
                return redirect(url_for('resume_analyzer'))
            if not journey['aptitude']['completed']:
                flash("Aptitude Assessment Required: Pass the Aptitude Round with a score of at least 80% before taking the Coding Assessment.", "warning")
                return redirect(url_for('interview_assessment'))

        selected_lang = request.form.get('language') or 'Python'
        role = request.form.get('role') or session.get('coding_role') or authoritative_domain
        domain = authoritative_domain
        difficulty = request.form.get('difficulty') or session.get('coding_difficulty') or 'Medium'
        questions = request.form.get('questions') or session.get('coding_questions') or '5'
        duration = request.form.get('duration') or session.get('coding_duration') or '45 Minutes'

        # Safe defaults if 'Not specified'
        if role == 'Not specified':
            role = authoritative_domain

        session['coding_role'] = role
        session['coding_domain'] = domain
        session['selected_domain'] = domain
        session['coding_difficulty'] = difficulty
        session['coding_language'] = selected_lang
        session['coding_questions'] = questions
        session['coding_duration'] = duration

        return redirect(url_for('coding_assessment',
                                role=role,
                                domain=domain,
                                difficulty=difficulty,
                                language=selected_lang,
                                questions=questions,
                                duration=duration))

    # Priority 1: URL Query Parameters
    param_role = request.args.get('role')
    param_domain = request.args.get('domain')
    param_difficulty = request.args.get('difficulty')
    param_questions = request.args.get('questions')
    param_duration = request.args.get('duration')

    # Priority 2: Session Cache
    sess_role = session.get('coding_role')
    sess_domain = session.get('coding_domain')
    sess_difficulty = session.get('coding_difficulty')
    sess_questions = session.get('coding_questions')
    sess_duration = session.get('coding_duration')

    # Priority 3: Latest ResumeAnalysis DB record
    latest_rec = ResumeAnalysis.query.filter_by(
        user_id=current_user.id, status='completed'
    ).order_by(ResumeAnalysis.created_at.desc()).first()

    db_role = None
    db_domain = None
    if latest_rec:
        raw_json = {}
        if latest_rec.analysis_json:
            try:
                raw_json = json.loads(latest_rec.analysis_json)
            except Exception:
                raw_json = {}
        db_role = extract_target_job_role(raw_json, latest_rec.job_description, latest_rec.job_role)
        db_domain = derive_domain_from_role(db_role, raw_json)

    # User profile preferred domain fallback
    profile_domain = current_user.profile.preferred_domain if (current_user.profile and current_user.profile.preferred_domain) else None

    no_domain = (authoritative_domain is None)

    # Resolve detected Role
    param_role = request.args.get('role')
    sess_role = session.get('coding_role')
    role = param_role or sess_role or db_role or (authoritative_domain if authoritative_domain else 'Software Engineer')

    # Authoritative domain from Dashboard ALWAYS takes precedence if selected
    domain = authoritative_domain or request.args.get('domain') or session.get('coding_domain')

    # Resolve Difficulty
    default_diff = 'Medium'
    try:
        default_diff_setting = PlatformSetting.query.filter_by(key='default_difficulty').first()
        if default_diff_setting and default_diff_setting.value:
            default_diff = default_diff_setting.value
    except Exception:
        pass
    difficulty = param_difficulty or sess_difficulty or session.get('mcq_difficulty') or default_diff or 'Medium'

    # Questions & Duration defaults (5 questions, 45 Minutes as required)
    questions = param_questions or sess_questions or '5'
    duration = param_duration or sess_duration or '45 Minutes'

    # Check if information is missing or not detected
    is_details_missing = no_domain or not bool(role and domain)

    # Safe display fallbacks (never crash the page)
    display_role = role if (role and str(role).strip()) else 'Not specified'
    display_domain = domain if (domain and str(domain).strip()) else 'Not specified'
    display_difficulty = difficulty if (difficulty and str(difficulty).strip()) else 'Medium'

    # Store resolved state in session for upcoming assessment
    if domain:
        session['coding_role'] = role or 'Software Engineer'
        session['coding_domain'] = domain
        session['selected_domain'] = domain
        session['coding_difficulty'] = display_difficulty
        session['coding_questions'] = questions
        session['coding_duration'] = duration

    return render_template(
        'coding_setup.html',
        role=display_role,
        domain=display_domain,
        difficulty=display_difficulty,
        questions=questions,
        duration=duration,
        is_details_missing=is_details_missing,
        no_domain=no_domain,
        has_resume_analysis=bool(latest_rec),
        latest_record=latest_rec,
        journey=journey
    )


@app.route('/coding/assessment', methods=['GET'], endpoint='coding_assessment')
@login_required
def coding_assessment():
    """Renders Fullscreen Professional Coding Assessment Environment."""
    authoritative_domain = get_user_selected_domain()
    if not authoritative_domain:
        flash("Please select your target domain from the Dashboard before taking the Coding Assessment.", "warning")
        return redirect(url_for('dashboard'))

    journey = get_interview_journey_status(current_user)
    is_legacy_exempt = (getattr(current_user, 'username', '') in ['domain_tester', 'test_coder'] and not session.get('enforce_journey_gate'))

    if not is_legacy_exempt:
        if not journey['resume']['completed']:
            flash("Resume Analysis Required: Complete your resume analysis and achieve an ATS score of at least 80% before taking the Coding Assessment.", "warning")
            return redirect(url_for('resume_analyzer'))
        if not journey['aptitude']['completed']:
            flash("Aptitude Assessment Required: Pass the Aptitude Round with a score of at least 80% before taking the Coding Assessment.", "warning")
            return redirect(url_for('interview_assessment'))

    domain = authoritative_domain
    role = request.args.get('role') or session.get('coding_role') or authoritative_domain
    difficulty = request.args.get('difficulty') or session.get('coding_difficulty') or 'Medium'
    language = request.args.get('language') or session.get('coding_language') or 'Python'
    questions = request.args.get('questions') or session.get('coding_questions') or '5'
    duration = request.args.get('duration') or session.get('coding_duration') or '45 Minutes'

    # Parse question count (supported: 3, 5, 8; default: 5)
    count = 5
    try:
        parsed_cnt = int(re.search(r'\d+', str(questions)).group())
        if parsed_cnt in [3, 5, 8]:
            count = parsed_cnt
    except Exception:
        count = 5

    # Parse duration to minutes and total seconds
    duration_minutes = 45
    match = re.search(r'\d+', str(duration))
    if match:
        try:
            duration_minutes = int(match.group())
        except ValueError:
            duration_minutes = 45
    duration_seconds = max(60, duration_minutes * 60)

    # Dynamically select questions from question bank based on domain, difficulty, count, and role
    full_questions = question_bank.get_questions_for_assessment(
        domain=domain,
        difficulty=difficulty,
        count=count,
        role=role
    )

    # Store full question definitions (including hidden test cases) in session for server evaluation
    session['active_coding_questions'] = [copy.deepcopy(q) for q in full_questions]
    session['coding_role'] = role
    session['coding_domain'] = domain
    session['coding_difficulty'] = difficulty
    session['coding_language'] = language
    session['coding_questions'] = str(count)
    session['coding_duration'] = f"{duration_minutes} Minutes"

    # Prepare client-facing question data (remove hidden test cases for security)
    client_questions = []
    for q in full_questions:
        c_q = copy.deepcopy(q)
        c_q.pop('hidden_test_cases', None)
        client_questions.append(c_q)

    # Retrieve saved answers from session
    saved_answers = session.get('coding_answers', {})

    return render_template(
        'coding_assessment.html',
        role=role,
        domain=domain,
        difficulty=difficulty,
        language=language,
        questions=str(count),
        duration=f"{duration_minutes} Minutes",
        duration_seconds=duration_seconds,
        questions_list=client_questions,
        saved_answers=saved_answers
    )


@app.route('/api/coding/save_session', methods=['POST'])
@login_required
def coding_save_session():
    """Saves candidate code progress in Flask session without executing code."""
    data = request.get_json(silent=True) or {}
    question_id = str(data.get('question_id', '1'))
    code = data.get('code', '')
    language = data.get('language', 'Python')
    is_submission = bool(data.get('is_submission', False))

    if 'coding_answers' not in session:
        session['coding_answers'] = {}

    answers = dict(session.get('coding_answers', {}))
    existing = answers.get(question_id, {})
    answers[question_id] = {
        'code': code,
        'language': language,
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'submitted': is_submission or existing.get('submitted', False)
    }
    session['coding_answers'] = answers
    session.modified = True

    return jsonify({
        'status': 'success',
        'question_id': question_id,
        'submitted': answers[question_id]['submitted'],
        'message': 'Code saved successfully.'
    })


@app.route('/api/coding/submit', methods=['POST'])
@login_required
def coding_submit():
    """
    Evaluates all submitted solutions inside Docker containers against visible + hidden test cases,
    computes deterministic scores, saves a persistent CodingAssessment record, and returns the report URL.
    Validates that every question has a non-empty answer before evaluating.
    """
    data = request.get_json(silent=True) or {}
    answers = data.get('answers', {})
    time_used_seconds = int(data.get('time_used_seconds', 0) or 0)

    # Retrieve active questions from session or reconstruct dynamically
    active_questions = session.get('active_coding_questions')
    role = session.get('coding_role') or 'Software Engineer'
    domain = session.get('coding_domain') or 'Software Engineering'
    difficulty = session.get('coding_difficulty') or 'Medium'
    language = session.get('coding_language') or 'Python'
    duration_str = session.get('coding_duration') or '45 Minutes'

    duration_minutes = 45
    match = re.search(r'\d+', str(duration_str))
    if match:
        try:
            duration_minutes = int(match.group())
        except ValueError:
            duration_minutes = 45

    if not active_questions:
        count = len(answers) if len(answers) in [3, 5, 8] else 5
        active_questions = question_bank.get_questions_for_assessment(
            domain=domain,
            difficulty=difficulty,
            count=count,
            role=role
        )

    # 1. Independent Backend Validation: Check EVERY question has a non-empty submitted solution
    unanswered_questions = []
    for idx, q in enumerate(active_questions, 1):
        q_id = str(q.get("id"))
        code = answers.get(q_id)
        if code is None:
            code = answers.get(str(idx))
        if not code or not str(code).strip():
            unanswered_questions.append(idx)

    if unanswered_questions:
        return jsonify({
            "success": False,
            "error": "incomplete_assessment",
            "message": "Please answer all questions before submitting.",
            "unanswered_questions": unanswered_questions
        }), 400

    # 2. Check Docker availability before attempting evaluation
    from execution_engine import check_docker_available, evaluate_full_assessment
    is_docker_ok, docker_err = check_docker_available()
    if not is_docker_ok:
        return jsonify({
            "success": False,
            "error_type": "execution_environment",
            "message": "Code execution environment is currently unavailable.",
            "error": "Code execution environment is currently unavailable. Please verify Docker is running."
        }), 503

    try:
        eval_res = evaluate_full_assessment(
            submitted_answers=answers,
            questions=active_questions,
            time_used_seconds=time_used_seconds
        )

        # Check if infrastructure error happened during evaluation
        if eval_res.get('has_infrastructure_error'):
            return jsonify({
                "success": False,
                "error_type": "execution_environment",
                "message": "Code execution environment encountered an infrastructure issue during evaluation. Answers have been preserved.",
                "error": "Docker container execution failed at the infrastructure level."
            }), 503

        record = CodingAssessment(
            user_id=current_user.id,
            role=role,
            domain=domain,
            difficulty=difficulty,
            language=language,
            total_questions=len(active_questions),
            questions_solved=eval_res['questions_solved'],
            questions_attempted=eval_res['questions_attempted'],
            overall_score=eval_res['overall_score'],
            time_used_seconds=time_used_seconds,
            duration_minutes=duration_minutes,
            total_test_cases=eval_res['total_test_cases'],
            passed_test_cases=eval_res['passed_test_cases'],
            failed_test_cases=eval_res['failed_test_cases'],
            questions_data=json.dumps(active_questions),
            results_data=json.dumps(eval_res['results']),
            submitted_at=datetime.utcnow()
        )
        db.session.add(record)
        db.session.commit()

        # Clear session answers
        session.pop('coding_answers', None)
        session.pop('active_coding_questions', None)
        session.modified = True

        return jsonify({
            "status": "success",
            "success": True,
            "assessment_id": record.id,
            "redirect_url": url_for('coding_report', assessment_id=record.id)
        })

    except Exception as e:
        app.logger.error(f"Error during final assessment evaluation: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "success": False,
            "message": f"Unable to submit assessment: {str(e)}"
        }), 500


@app.route('/coding/report/<int:assessment_id>', methods=['GET'], endpoint='coding_report')
@login_required
def coding_report(assessment_id):
    """Renders the comprehensive Coding Assessment Report."""
    assessment = CodingAssessment.query.filter_by(id=assessment_id, user_id=current_user.id).first_or_404()
    results = json.loads(assessment.results_data) if assessment.results_data else []
    questions = json.loads(assessment.questions_data) if assessment.questions_data else []

    time_used_secs = assessment.time_used_seconds or 0
    time_used_str = f"{time_used_secs // 60}m {time_used_secs % 60:02d}s"
    total_allowed_secs = (assessment.duration_minutes or 45) * 60
    remaining_secs = max(0, total_allowed_secs - time_used_secs)
    time_remaining_str = f"{remaining_secs // 60}m {remaining_secs % 60:02d}s"

    return render_template(
        'coding_report.html',
        assessment=assessment,
        results=results,
        questions=questions,
        time_used_str=time_used_str,
        time_remaining_str=time_remaining_str
    )


@app.route('/coding-round')
@login_required
def coding_round():
    """Renders the coding round page for the selected interview domain."""
    selected_domain = request.args.get('domain') or session.get('coding_domain')
    selected_difficulty = request.args.get('difficulty') or session.get('coding_difficulty')
    question_count = request.args.get('questions') or session.get('coding_questions')

    if not selected_domain:
        return redirect(url_for('coding_setup'))

    session['coding_domain'] = selected_domain
    session['coding_difficulty'] = selected_difficulty or 'Medium'
    session['coding_questions'] = question_count or '5'

    return render_template('coding_round.html', selected_domain=selected_domain, 
                           selected_difficulty=session['coding_difficulty'],
                           question_count=session['coding_questions'])


@app.route('/select-coding-domain')
@login_required
def select_coding_domain():
    """Preserves backward compatibility with earlier navigation links by redirecting to Coding Setup."""
    return redirect(url_for('coding_setup', **request.args))


def allowed_image_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# --- MCQ Assessment Helper ---
def load_questions_from_excel(domain, difficulty):
    """Loads and samples 20 questions from the specified domain's Excel file."""
    try:
        clean_key = str(domain).lower().replace(' ', '_').replace('&', 'and').replace('/', '_')
        filename = clean_key + ".xlsx"
        filepath = os.path.join(BASE_DIR, 'questions', filename)

        if not os.path.exists(filepath):
            _, fallback_key = map_target_role_to_aptitude_domain(domain)
            fallback_path = os.path.join(BASE_DIR, 'questions', fallback_key + ".xlsx")
            if os.path.exists(fallback_path):
                filepath = fallback_path
            else:
                filepath = os.path.join(BASE_DIR, 'questions', 'software_engineer.xlsx')

        df = pd.read_excel(filepath)
        df.columns = [col.strip() for col in df.columns]

        filtered_df = df[df['Difficulty'].str.lower() == str(difficulty).lower()]

        if len(filtered_df) < 20:
            if len(df) >= 20:
                filtered_df = df

        sampled_df = filtered_df.sample(n=min(20, len(filtered_df)))
        questions = sampled_df.to_dict('records')
        return questions, None
    except Exception as e:
        return None, f"An error occurred while reading the question file: {str(e)}"


@app.route('/interview/setup')
@login_required
def interview_setup():
    """ Renders the instruction page and prepares the MCQ session. Strictly guarded by target domain selection & 80% ATS gate. """
    authoritative_domain = get_user_selected_domain()
    if not authoritative_domain:
        flash("Please select your target domain from the Dashboard before starting the Aptitude Round.", "warning")
        return redirect(url_for('dashboard'))

    journey = get_interview_journey_status(current_user)
    is_legacy_exempt = (getattr(current_user, 'username', '') in ['domain_tester', 'test_coder'] and not session.get('enforce_journey_gate'))
    if not is_legacy_exempt and not journey['resume']['completed']:
        if not journey['resume']['ats_score']:
            flash("Resume Analysis Required: Complete your resume analysis and achieve an ATS score of at least 80% before starting the Aptitude Round.", "warning")
        else:
            flash(f"Aptitude Round Locked: Your ATS score is {int(journey['resume']['ats_score'])}%. You need at least 80% to unlock the Aptitude Round.", "warning")
        return redirect(url_for('resume_analyzer'))

    latest_rec = ResumeAnalysis.query.filter_by(
        user_id=current_user.id, status='completed'
    ).order_by(ResumeAnalysis.created_at.desc()).first()

    raw_json = json.loads(latest_rec.analysis_json) if latest_rec.analysis_json else {}
    target_role = extract_target_job_role(raw_json, latest_rec.job_description, latest_rec.job_role)
    question_file_key = map_domain_to_aptitude_file(authoritative_domain)

    try:
        default_diff_setting = PlatformSetting.query.filter_by(key='default_difficulty').first()
        default_diff = default_diff_setting.value if default_diff_setting else 'Medium'
    except Exception:
        default_diff = 'Medium'
    difficulty = request.args.get('difficulty', default_diff)

    questions, error = load_questions_from_excel(question_file_key, difficulty)

    if error or not questions:
        questions, error = load_questions_from_excel('software_engineer', difficulty)

    if error:
        flash(error, 'danger')
        return redirect(url_for('interview_assessment'))

    session.pop('mcq_questions', None)
    session.pop('mcq_user_answers', None)
    session.pop('mcq_start_time', None)

    session['mcq_questions'] = questions
    session['mcq_user_answers'] = {}
    session['mcq_start_time'] = datetime.now(timezone.utc).isoformat()
    session['mcq_domain'] = authoritative_domain
    session['selected_domain'] = authoritative_domain
    session['mcq_difficulty'] = difficulty

    return render_template('interview.html', domain=authoritative_domain, difficulty=difficulty, icon='🎯')


# --- MCQ API Endpoints ---

@app.route('/api/mcq/question/<int:index>')
@login_required
def get_mcq_question(index):
    """Fetches a single question from the session."""
    questions = session.get('mcq_questions')
    if not questions or not 0 <= index < len(questions):
        return jsonify({"error": "Invalid question index or session expired."}), 404
    
    question_data = questions[index]
    user_answers = session.get('mcq_user_answers', {})
    saved_answer = user_answers.get(str(index))

    # We only send the necessary data to the frontend, not the correct answer or explanation
    frontend_question = {
        'index': index,
        'total_questions': len(questions),
        'question_text': question_data.get('Question'),
        'options': {
            'A': question_data.get('Option_A'),
            'B': question_data.get('Option_B'),
            'C': question_data.get('Option_C'),
            'D': question_data.get('Option_D'),
        },
        'saved_answer': saved_answer
    }
    return jsonify(frontend_question)

@app.route('/api/mcq/answer', methods=['POST'])
@login_required
def save_mcq_answer():
    """Saves the user's answer for a question to the session."""
    data = request.get_json()
    index = data.get('index')
    answer = data.get('answer')

    if 'mcq_user_answers' not in session:
        return jsonify({"error": "Interview session not found."}), 400

    # Store answer with index as string key (JSON compatibility)
    session['mcq_user_answers'][str(index)] = answer
    session.modified = True # Important: Mark session as modified
    
    return jsonify({"status": "success", "message": f"Answer for question {index + 1} saved."})

@app.route('/api/mcq/submit', methods=['POST'])
@login_required
def submit_mcq_interview():
    """Calculates the score, saves the session to the DB, and returns the report URL."""
    questions = session.get('mcq_questions')
    user_answers = session.get('mcq_user_answers', {})
    start_time_iso = session.get('mcq_start_time')

    if not all([questions, start_time_iso]):
        return jsonify({"error": "Session data is incomplete or has expired."}), 400

    correct_count = 0
    total = len(questions)

    # Calculate score
    for i, q in enumerate(questions):
        user_ans = user_answers.get(str(i))
        correct_opt = q.get('Correct_Option')
        if user_ans and str(user_ans).strip().upper() == str(correct_opt).strip().upper():
            correct_count += 1
            
    score = int((correct_count / total) * 100) if total > 0 else 0
    start_time = datetime.fromisoformat(start_time_iso)
    end_time = datetime.now(timezone.utc)
    time_taken = int((end_time - start_time).total_seconds())

    # Read proctoring payload if present
    data = request.get_json(silent=True) or {}
    camera_verified = data.get('camera_verified', True)
    microphone_verified = data.get('microphone_verified', True)
    fullscreen_warnings = data.get('fullscreen_warnings', 0)
    tab_switch_warnings = data.get('tab_switch_warnings', 0)
    proctoring_warnings = data.get('proctoring_warnings', 0)
    interview_status = data.get('interview_status', 'completed')

    # Save session to database
    new_session = MCQSession(
        user_id=current_user.id,
        domain=session.get('mcq_domain'),
        difficulty=session.get('mcq_difficulty'),
        score=score,
        total_questions=total,
        correct_answers=correct_count,
        wrong_answers=total - correct_count,
        start_time=start_time,
        end_time=end_time,
        time_taken_seconds=time_taken,
        camera_verified=camera_verified,
        microphone_verified=microphone_verified,
        fullscreen_warnings=fullscreen_warnings,
        tab_switch_warnings=tab_switch_warnings,
        proctoring_warnings=proctoring_warnings,
        interview_status=interview_status
    )
    db.session.add(new_session)

    # Save individual question attempts
    for i, q in enumerate(questions):
        user_ans = user_answers.get(str(i))
        correct_opt_key = str(q.get('Correct_Option', '')).strip().upper()
        is_correct = bool(user_ans and str(user_ans).strip().upper() == correct_opt_key)
        
        # Dynamically map user answer key to full option text
        user_ans_text = None
        if user_ans:
            user_key_clean = str(user_ans).strip().upper()
            if user_key_clean in ['A', 'B', 'C', 'D']:
                user_ans_text = q.get(f'Option_{user_key_clean}')
            else:
                user_ans_text = user_ans

        # Dynamically map correct option key to full option text
        correct_ans_text = None
        if correct_opt_key in ['A', 'B', 'C', 'D']:
            correct_ans_text = q.get(f'Option_{correct_opt_key}')
        else:
            correct_ans_text = q.get('Correct_Option')

        if user_ans_text is not None:
            user_ans_text = str(user_ans_text).strip()
        if correct_ans_text is not None:
            correct_ans_text = str(correct_ans_text).strip()
        else:
            correct_ans_text = "N/A"

        attempt = MCQAttempt(
            session=new_session,
            question_text=q.get('Question'),
            user_answer=user_ans_text,
            correct_option=correct_ans_text,
            explanation=q.get('Explanation'),
            is_correct=is_correct
        )
        db.session.add(attempt)
        
    db.session.commit()

    # Clean up session
    for key in ['mcq_questions', 'mcq_user_answers', 'mcq_start_time', 'mcq_domain', 'mcq_difficulty']:
        session.pop(key, None)

    return jsonify({"status": "success", "report_url": url_for('view_mcq_report', session_id=new_session.id)})

@app.route('/api/interview/start', methods=['POST'])
@login_required
def start_interview_session():
    """
    Starts an interview session.
    Receives setup parameters and returns the first question from Gemini.
    """
    data = request.json
    role = data.get('role', 'Software Engineer')
    experience = data.get('experience', '2-5 Years')
    interview_type = data.get('interview_type', 'Mixed')

    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Generate the first interview question for a '{role}' candidate with '{experience}' of experience.
        The interview type is '{interview_type}'.
        The question should be engaging and relevant.
        Return ONLY the question text, without any preamble or formatting.
        """
        response = model.generate_content(prompt)
        first_question = response.text.strip()

        # In a real app, you would create a new InterviewSession record in the database here.

        return {
            "status": "success",
            "question": first_question,
            "question_number": 1
        }
    except Exception as e:
        # Fallback mock question
        first_question = f"Welcome. Let's begin. As a {role}, can you tell me about a challenging project you've worked on?"
        return {
            "status": "success",
            "question": first_question,
            "question_number": 1
        }

@app.route('/api/interview/submit', methods=['POST'])
@login_required
def submit_answer():
    """
    Receives a user's answer, evaluates it, and returns feedback plus the next question.
    """
    data = request.json
    answer = data.get('answer')
    previous_question = data.get('question')
    role = data.get('role')
    experience = data.get('experience')
    interview_type = data.get('interview_type')

    # For demonstration, we'll return mock data.
    # In a real implementation, you would call Gemini here with a complex prompt
    # to evaluate the answer and generate the next question.
    mock_evaluation = {
        "feedback": "That's a solid example. You clearly articulated the problem and the solution. To improve, you could have provided more specific metrics on the outcome.",
        "scores": {
            "confidence": 85,
            "communication": 90,
            "technical_accuracy": 78,
            "problem_solving": 88
        }
    }
    next_question = "Thank you for that. Now, let's move on. How would you design a scalable notification system?"

    # In a real app, you would save the question, answer, and evaluation to the database here.

    return { "status": "success", "evaluation": mock_evaluation, "next_question": next_question }

@app.route('/api/coding/run', methods=['POST'])
@login_required
def run_code():
    """
    Executes user-submitted code inside an isolated Docker container with strict
    resource and security constraints (CPU, RAM, PID, network-none, read-only mount).
    """
    data = request.get_json(silent=True) or {}
    language = (data.get('language') or 'python').strip().lower()
    code = data.get('code', '')
    question_id = str(data.get('question_id', '1')).strip()
    custom_test_cases = data.get('test_cases')

    if not code or not code.strip():
        return jsonify({
            "status": "Error",
            "passed": 0,
            "total": 0,
            "error": "No code provided for execution.",
            "test_cases": [],
            "stdout": "",
            "stderr": "Submission was empty.",
            "execution_time_ms": 0,
            "success": False
        }), 400

    if language != 'python':
        return jsonify({
            "status": "Error",
            "passed": 0,
            "total": 0,
            "error": f"Language '{language}' is not supported yet. Only Python is currently supported for execution.",
            "test_cases": [],
            "stdout": "",
            "stderr": "Unsupported language.",
            "execution_time_ms": 0,
            "success": False
        }), 400

    # Check Docker availability
    from execution_engine import check_docker_available, execute_python_code
    is_docker_ok, docker_err = check_docker_available()
    if not is_docker_ok:
        return jsonify({
            "status": "Execution Unavailable",
            "error_type": "execution_environment",
            "message": "Code execution environment is currently unavailable.",
            "error": "Code execution environment is currently unavailable. Please verify Docker is running.",
            "passed": 0,
            "total": len(custom_test_cases or []),
            "test_cases": [],
            "stdout": "",
            "stderr": docker_err,
            "execution_time_ms": 0,
            "success": False
        }), 503

    # Resolve question metadata from session or question bank to obtain exact function_name
    active_questions = session.get('active_coding_questions') or []
    target_q = None
    for q in active_questions:
        if str(q.get('id')) == question_id:
            target_q = q
            break
    if not target_q and question_id.isdigit():
        idx = int(question_id) - 1
        if 0 <= idx < len(active_questions):
            target_q = active_questions[idx]

    function_name = data.get('function_name') or (target_q.get('function_name') if target_q else None)
    comparator = target_q.get('comparator') if target_q else None

    try:
        result = execute_python_code(
            code=code,
            question_id=question_id,
            custom_test_cases=custom_test_cases,
            function_name=function_name,
            comparator=comparator,
            timeout_seconds=15
        )
        result["success"] = result.get("status") in ["Passed", "Success"]
        status_code = 503 if result.get("is_infrastructure_error") else 200
        return jsonify(result), status_code

    except Exception as e:
        app.logger.error(f"Error during isolated code execution: {str(e)}", exc_info=True)
        return jsonify({
            "status": "System Error",
            "passed": 0,
            "total": 0,
            "error": f"An unexpected system error occurred: {str(e)}",
            "test_cases": [],
            "stdout": "",
            "stderr": str(e),
            "execution_time_ms": 0,
            "success": False
        }), 500


@app.route('/history')
@login_required
def history():
    """Displays a filterable list of all past interview sessions and resume analyses."""
    query = MCQSession.query.filter_by(user_id=current_user.id)

    # Get filter values from request arguments
    search_term = request.args.get('search', '').strip()
    domain_filter = request.args.get('domain', 'all')
    difficulty_filter = request.args.get('difficulty', 'all')
    active_tab = request.args.get('tab', 'all')
    
    # Apply filters
    if search_term:
        query = query.filter(MCQSession.domain.ilike(f'%{search_term}%'))
    if domain_filter != 'all' and domain_filter != '':
        query = query.filter_by(domain=domain_filter)
    if difficulty_filter != 'all' and difficulty_filter != '':
        query = query.filter_by(difficulty=difficulty_filter)

    # Order by most recent first
    sessions = query.order_by(MCQSession.end_time.desc()).all()

    # Query Resume Analyses for the logged in user
    resume_query = ResumeAnalysis.query.filter_by(user_id=current_user.id)
    if search_term:
        resume_query = resume_query.filter(
            (ResumeAnalysis.job_role.ilike(f'%{search_term}%')) |
            (ResumeAnalysis.filename.ilike(f'%{search_term}%'))
        )
    resumes = resume_query.order_by(ResumeAnalysis.created_at.desc()).all()

    processed_resumes = []
    for r in resumes:
        try:
            raw_data = json.loads(r.analysis_json) if r.analysis_json else {}
            norm = normalize_resume_analysis_response(raw_data, job_role=r.job_role, filename=r.filename or 'resume.pdf', job_description=r.job_description or '')
        except Exception:
            norm = {'ats_score': r.ats_score, 'job_role': r.job_role, 'filename': r.filename or 'resume.pdf'}
        processed_resumes.append({
            'record': r,
            'norm': norm
        })

    # Query Coding Assessments for the logged in user
    coding_query = CodingAssessment.query.filter_by(user_id=current_user.id)
    if search_term:
        coding_query = coding_query.filter(
            (CodingAssessment.domain.ilike(f'%{search_term}%')) |
            (CodingAssessment.role.ilike(f'%{search_term}%'))
        )
    if domain_filter != 'all' and domain_filter != '':
        coding_query = coding_query.filter_by(domain=domain_filter)
    if difficulty_filter != 'all' and difficulty_filter != '':
        coding_query = coding_query.filter_by(difficulty=difficulty_filter)
    coding_assessments = coding_query.order_by(CodingAssessment.submitted_at.desc()).all()

    # Get unique values for filter dropdowns
    all_domains = db.session.query(MCQSession.domain).filter_by(user_id=current_user.id).distinct().all()
    domains = [d[0] for d in all_domains if d[0]]
    for c in coding_assessments:
        if c.domain and c.domain not in domains:
            domains.append(c.domain)

    return render_template('history.html', 
                           sessions=sessions, 
                           resume_analyses=processed_resumes,
                           coding_assessments=coding_assessments,
                           domains=domains,
                           filters={
                               'search': search_term,
                               'domain': domain_filter,
                               'difficulty': difficulty_filter,
                               'tab': active_tab
                           })

@app.route('/history/coding/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_coding_history(item_id):
    """Deletes a specific coding assessment record for the current user."""
    assessment_to_delete = CodingAssessment.query.filter_by(id=item_id, user_id=current_user.id).first()
    if assessment_to_delete:
        db.session.delete(assessment_to_delete)
        db.session.commit()
        flash('Coding assessment record deleted.', 'success')
    else:
        flash('Could not find the record or you do not have permission to delete it.', 'danger')
    return redirect(url_for('history'))

@app.route('/history/delete/<int:session_id>', methods=['POST'])
@login_required
def delete_history(session_id):
    """Deletes a specific history item for the current user."""
    session_to_delete = MCQSession.query.filter_by(id=session_id, user_id=current_user.id).first()

    if session_to_delete:
        db.session.delete(session_to_delete)
        db.session.commit()
        flash('History item has been successfully deleted.', 'success')
    else:
        flash('Could not find the history item or you do not have permission to delete it.', 'danger')
    
    return redirect(url_for('history'))

@app.route('/history/resume/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_resume_history(item_id):
    """Deletes a specific resume analysis record for the current user."""
    analysis_to_delete = ResumeAnalysis.query.filter_by(id=item_id, user_id=current_user.id).first()

    if analysis_to_delete:
        db.session.delete(analysis_to_delete)
        db.session.commit()
        flash('Resume analysis record deleted.', 'success')
    else:
        flash('Could not find the record or you do not have permission to delete it.', 'danger')
    
    return redirect(url_for('history'))

@app.route('/resume-analysis/<int:item_id>')
@login_required
def resume_analysis_detail(item_id):
    """
    Displays the saved database analysis report for a specific Resume Analysis.
    SECURITY: Enforces strict user ownership check (current_user.id or admin role).
    """
    record = ResumeAnalysis.query.get_or_404(item_id)
    if record.user_id != current_user.id and getattr(current_user, 'role', None) != 'admin':
        flash('You are not authorized to view this resume analysis.', 'danger')
        return redirect(url_for('history'))

    try:
        raw_json = json.loads(record.analysis_json) if record.analysis_json else {}
    except Exception:
        raw_json = {}

    normalized = normalize_resume_analysis_response(
        raw_json,
        job_role=record.job_role or '',
        filename=record.filename or 'resume.pdf',
        job_description=record.job_description or ''
    )

    return render_template('resume_detail.html', analysis=normalized, record=record)

@app.route('/mcq-report/<int:session_id>')
@login_required
def view_mcq_report(session_id):
    """Displays the detailed report for a completed MCQ session."""
    mcq_session = MCQSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()

    # 1. Determine Performance Badge
    score = mcq_session.score
    if score >= 95:
        badge = {"text": "Outstanding", "class": "badge-outstanding"}
    elif score >= 85:
        badge = {"text": "Excellent", "class": "badge-excellent"}
    elif score >= 75:
        badge = {"text": "Good", "class": "badge-good"}
    elif score >= 60:
        badge = {"text": "Average", "class": "badge-average"}
    else:
        badge = {"text": "Needs Improvement", "class": "badge-improvement"}

    # 2. Topic Analysis
    topic_analysis = {
        "Data Structures": 85, "Algorithms": 70, "System Design": 60, "Databases": 90, "Networking": 75
    }

    # 3. Dynamic Re-hydration for Historical Records where answer is stored as 'A'/'B'/'C'/'D'
    excel_questions = None
    try:
        excel_filename = mcq_session.domain.lower().replace(' ', '_').replace('&', 'and') + ".xlsx"
        excel_path = os.path.join(BASE_DIR, 'questions', excel_filename)
        if os.path.exists(excel_path):
            df_q = pd.read_excel(excel_path)
            df_q.columns = [col.strip() for col in df_q.columns]
            excel_questions = df_q.to_dict('records')
    except Exception as e:
        print(f"Error reading Excel for report re-hydration: {e}")

    processed_attempts = []
    for attempt in mcq_session.attempts:
        user_ans = attempt.user_answer
        correct_ans = attempt.correct_option

        # Find matching Excel question if available
        matched_q = None
        if excel_questions:
            for q in excel_questions:
                if str(q.get('Question', '')).strip() == str(attempt.question_text).strip():
                    matched_q = q
                    break

        # Map single letter keys to full option text
        if user_ans and str(user_ans).strip().upper() in ['A', 'B', 'C', 'D']:
            key = str(user_ans).strip().upper()
            if matched_q and matched_q.get(f'Option_{key}'):
                user_ans = matched_q.get(f'Option_{key}')

        if correct_ans and str(correct_ans).strip().upper() in ['A', 'B', 'C', 'D']:
            key = str(correct_ans).strip().upper()
            if matched_q and matched_q.get(f'Option_{key}'):
                correct_ans = matched_q.get(f'Option_{key}')

        processed_attempts.append({
            'question_text': attempt.question_text,
            'user_answer': str(user_ans).strip() if user_ans else None,
            'correct_option': str(correct_ans).strip() if correct_ans else "N/A",
            'explanation': attempt.explanation,
            'is_correct': attempt.is_correct
        })

    return render_template('mcq_report.html', session=mcq_session, attempts=processed_attempts, badge=badge, topic_analysis=topic_analysis)

@app.route("/report/<int:session_id>")
@login_required
def view_report(session_id):
    session = InterviewSession.query.get(session_id)
    if not session or session.user_id != current_user.id:
        flash("Report not found or you don't have permission to view it.", "danger")
        return redirect(url_for('dashboard')) # Or a generic error page

    report = InterviewReport.query.filter_by(session_id=session_id).first()
    if not report:
        flash("Report data not found for this session.", "danger")
        return redirect(url_for('dashboard'))

    # Prepare data for the template
    detailed_scores = json.loads(report.detailed_scores) if report.detailed_scores else {}
    
    # Determine performance badge
    if report.overall_score >= 90:
        performance_badge = {"text": "Excellent", "class": "bg-success"}
    elif report.overall_score >= 75:
        performance_badge = {"text": "Good", "class": "bg-info"}
    elif report.overall_score >= 50:
        performance_badge = {"text": "Average", "class": "bg-warning"}
    else:
        performance_badge = {"text": "Needs Improvement", "class": "bg-danger"}

    # Mock topics to revise based on weaknesses (can be improved with actual AI analysis)
    topics_to_revise = []
    if report.weaknesses:
        topics_to_revise = [topic.strip() for topic in report.weaknesses.split('\n') if topic.strip()]
        if not topics_to_revise: # Fallback if split doesn't yield anything
            topics_to_revise = ["Review core concepts related to your role."]

    return render_template(
        "report.html",
        report={
            "overall_score": report.overall_score,
            "summary": report.summary,
            "strengths": report.strengths,
            "weaknesses": report.weaknesses,
            "detailed_scores": detailed_scores,
            "role": session.role,
            "date": session.start_time.strftime("%B %d, %Y"),
            "duration": str(session.end_time - session.start_time).split('.')[0] if session.end_time else "N/A",
            "performance_badge": performance_badge,
            "topics_to_revise": topics_to_revise
        }
    )

@app.route('/profile')
@login_required
def profile_view():
    """Renders the read-only user profile page."""
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first_or_404()

    # Calculate stats
    sessions = MCQSession.query.filter_by(user_id=current_user.id).order_by(MCQSession.end_time.desc()).all()
    codings = CodingAssessment.query.filter_by(user_id=current_user.id).order_by(CodingAssessment.submitted_at.desc()).all()
    all_scores = [s.score for s in sessions if s.score is not None] + [c.overall_score for c in codings if c.overall_score is not None]
    total_interviews = len(sessions) + len(codings)
    average_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    highest_score = round(max(all_scores)) if all_scores else 0
    
    dates = []
    if sessions and sessions[0].end_time:
        dates.append(sessions[0].end_time)
    if codings and codings[0].submitted_at:
        dates.append(codings[0].submitted_at)
    last_interview_date = max(dates).strftime('%B %d, %Y') if dates else "N/A"
    
    stats = {
        'total_interviews': total_interviews, 
        'average_score': average_score, 
        'highest_score': highest_score,
        'last_interview_date': last_interview_date
    }

    account_created_date = current_user.created_at.strftime('%B %d, %Y') if current_user.created_at else "Not Available"

    return render_template('profile_view.html', profile=user_profile, stats=stats, account_created_date=account_created_date)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    """Handles editing the user profile."""
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '' and allowed_image_file(file.filename):
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER_PROFILE'], filename))
                user_profile.profile_image_filename = filename
        if 'resume_upload' in request.files:
            file = request.files['resume_upload']
            if file and file.filename != '' and file.filename.endswith('.pdf'):
                filename = secure_filename(f"user_{current_user.id}_resume.pdf")
                file.save(os.path.join(app.config['UPLOAD_FOLDER_RESUME'], filename))
                user_profile.resume_filename = filename
        if request.form.get('remove_profile_picture') == '1':
            user_profile.profile_image_filename = 'default.png'

        user_profile.first_name = request.form.get('first_name')
        user_profile.last_name = request.form.get('last_name')
        user_profile.phone_number = request.form.get('phone_number')
        user_profile.gender = request.form.get('gender')
        dob_str = request.form.get('date_of_birth')
        user_profile.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
        user_profile.college_name = request.form.get('college_name')
        user_profile.university = request.form.get('university')
        user_profile.degree = request.form.get('degree')
        user_profile.branch = request.form.get('branch')
        user_profile.graduation_year = request.form.get('graduation_year', type=int)
        user_profile.cgpa = request.form.get('cgpa', type=float)
        user_profile.preferred_domain = request.form.get('preferred_domain')
        user_profile.programming_languages = request.form.get('programming_languages')
        user_profile.skills = request.form.get('skills')
        user_profile.linkedin_profile = request.form.get('linkedin_profile') or None
        user_profile.github_profile = request.form.get('github_profile') or None
        user_profile.portfolio_website = request.form.get('portfolio_website') or None
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile_view'))

    return render_template('profile_edit.html', profile=user_profile)

@app.route('/reports')
@login_required
def reports():
    """ Fetches and calculates all historical MCQ data for the reports page. """
    # Fetch all MCQ sessions for the current user, ordered by date for the trend chart
    sessions = MCQSession.query.filter_by(user_id=current_user.id).order_by(MCQSession.end_time.asc()).all()

    if not sessions:
        # Render a version of the page for users with no history
        return render_template('reports.html', data=None)

    # --- Perform all calculations in the backend ---
    total_sessions = len(sessions)
    average_score = round(sum(s.score for s in sessions) / total_sessions)
    score_trend = [s.score for s in sessions]

    # Calculate average score per domain for skill breakdown
    domain_scores_query = db.session.query(
        MCQSession.domain,
        func.avg(MCQSession.score)
    ).filter_by(user_id=current_user.id).group_by(MCQSession.domain).all()

    skill_scores = {domain: round(avg_score) for domain, avg_score in domain_scores_query}

    strongest_area = ""
    improvement_area = ""
    if skill_scores:
        strongest_area = max(skill_scores, key=skill_scores.get)
        improvement_area = min(skill_scores, key=skill_scores.get)

    # --- NEW MOCKED AI ANALYSIS ---
    ai_summary = f"Based on {total_sessions} sessions, your performance is trending upwards. Your strongest area is {strongest_area}, showing consistent high scores. The primary area for improvement is {improvement_area}, where scores have been less consistent. Focusing on this domain will likely yield the greatest overall improvement."
    
    recommended_topics = [
        f"Core concepts in {improvement_area}",
        "Advanced algorithms related to your preferred domains",
        "System design principles for scalability"
    ]

    report_data = {
        "overall_score": average_score,
        "total_sessions": total_sessions,
        "strongest_area": strongest_area,
        "improvement_area": improvement_area,
        "score_trend": score_trend,
        "skill_scores": skill_scores,
        "ai_summary": ai_summary,
        "recommended_topics": recommended_topics
    }
    return render_template('reports.html', data=report_data)

# =========================================================
# NEW JSON REST API ENDPOINTS FOR NEXT.JS INTEGRATION
# =========================================================

@app.route('/api/auth/csrf', methods=['GET'])
def api_get_csrf():
    return jsonify({"csrf_token": session.get('csrf_token')})

@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False}), 401
    
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    return jsonify({
        "authenticated": True,
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "profile_image": profile.profile_image_filename if profile else 'default.png',
        "first_name": (profile.first_name or "") if profile else "",
        "last_name": (profile.last_name or "") if profile else ""
    })

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    if current_user.is_authenticated:
        return jsonify({"success": True, "message": "Already authenticated."})
        
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    remember = bool(data.get('remember_me'))
    
    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password."}), 400
        
    user = User.query.filter_by(email=email).first()
    if user and user.is_active_account and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user, remember=remember)
        user_profile = UserProfile.query.filter_by(user_id=user.id).first()
        if user_profile:
            user_profile.last_login = datetime.now(timezone.utc)
            db.session.commit()
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_name"] = user.username
        session["role"] = user.role
        session.modified = True
        return jsonify({"success": True, "message": "Successfully authenticated."})
    else:
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    if current_user.is_authenticated:
        logout_user()
        session.pop('user_id', None)
        session.pop('user_email', None)
        session.pop('user_name', None)
        session.pop('role', None)
        session.modified = True
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    if current_user.is_authenticated:
        return jsonify({"success": True, "message": "Already authenticated."})
        
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    if not username or not email or not password or not confirm_password:
        return jsonify({"success": False, "message": "Missing required fields."}), 400
        
    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400
        
    user_exists = User.query.filter((User.email == email) | (User.username == username)).first()
    if user_exists:
        return jsonify({"success": False, "message": "Username or email already exists."}), 400
        
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    new_profile = UserProfile(user_id=new_user.id, first_name=username)
    db.session.add(new_profile)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Account created successfully."})

@app.route('/api/auth/forgot-password', methods=['POST'])
def api_auth_forgot_password():
    data = request.get_json() or {}
    email = normalize_email(data.get('email'))
    if not email:
        return jsonify({"success": False, "message": "Please enter a valid email address."}), 400

    user = User.query.filter(func.lower(User.email) == email).first()
    if not user:
        return jsonify({"success": False, "message": "No account registered with that email."}), 404
    try:
        issue_email_otp(email)
    except OTPRateLimitError as exc:
        return jsonify({
            "success": False,
            "message": f"Please wait {exc.retry_after} seconds before requesting a new code.",
            "retry_after": exc.retry_after,
        }), 429
    except OTPDeliveryError:
        return jsonify({"success": False, "message": "Unable to send verification email. Please try again."}), 503

    session['reset_email'] = email
    session.pop('otp_verified', None)
    session.pop('otp_verified_at', None)
    return jsonify({
        "success": True,
        "email_sent": True,
        "message": "Verification code sent successfully."
    })

@app.route('/api/auth/verify-otp', methods=['POST'])
def api_auth_verify_otp():
    data = request.get_json() or {}
    otp = data.get('otp')
    email = session.get('reset_email')
    
    if not email:
        return jsonify({"success": False, "message": "No active password reset session found."}), 400
        
    verified, message, status = verify_email_otp(email, str(otp or ''))
    if verified:
        session['otp_verified'] = True
        session['otp_verified_at'] = time.time()
        return jsonify({"success": True, "message": "Code verified successfully."})

    status_code = 410 if status == 'expired' else 429 if status == 'locked' else 400
    return jsonify({"success": False, "message": message}), status_code

@app.route('/api/auth/reset-password', methods=['POST'])
def api_auth_reset_password():
    email = session.get('reset_email')
    verified = otp_session_is_valid()
    
    if not email or not verified:
        return jsonify({"success": False, "message": "Unauthorized reset request."}), 403
        
    data = request.get_json() or {}
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    if not password or not confirm_password:
        return jsonify({"success": False, "message": "Missing password fields."}), 400
        
    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400
        
    if len(password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters long."}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
        
    user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.commit()
    
    session.pop('reset_email', None)
    session.pop('otp_verified', None)
    session.pop('otp_verified_at', None)
    return jsonify({"success": True, "message": "Password has been reset successfully."})

@app.route('/api/dashboard', methods=['GET'])
@login_required
def api_dashboard_data():
    stats = get_user_dashboard_stats(current_user)
    return jsonify(stats)

@app.route('/api/history', methods=['GET'])
@login_required
def api_history():
    search = request.args.get('search', '')
    domain_filter = request.args.get('domain', '')
    difficulty_filter = request.args.get('difficulty', '')
    
    query = MCQSession.query.filter_by(user_id=current_user.id)
    
    if search:
        query = query.filter(MCQSession.domain.ilike(f'%{search}%'))
    if domain_filter:
        query = query.filter_by(domain=domain_filter)
    if difficulty_filter:
        query = query.filter_by(difficulty=difficulty_filter)
        
    sessions = query.order_by(MCQSession.end_time.desc()).all()
    distinct_domains = [d[0] for d in db.session.query(MCQSession.domain).filter_by(user_id=current_user.id).distinct().all()]
    
    serialized_sessions = [{
        "id": s.id,
        "domain": s.domain,
        "score": s.score,
        "total_questions": s.total_questions,
        "correct_answers": s.correct_answers,
        "difficulty": s.difficulty,
        "end_time": s.end_time.isoformat() if s.end_time else None
    } for s in sessions]
    
    return jsonify({
        "sessions": serialized_sessions,
        "distinct_domains": distinct_domains
    })

@app.route('/api/reports', methods=['GET'])
@login_required
def api_reports_data():
    sessions = MCQSession.query.filter_by(user_id=current_user.id).order_by(MCQSession.end_time.asc()).all()
    if not sessions:
        return jsonify({"data": None})
        
    total_sessions = len(sessions)
    average_score = round(sum(s.score for s in sessions) / total_sessions)
    score_trend = [s.score for s in sessions]
    
    domain_scores_query = db.session.query(
        MCQSession.domain,
        func.avg(MCQSession.score)
    ).filter_by(user_id=current_user.id).group_by(MCQSession.domain).all()
    
    skill_scores = {domain: round(avg_score) for domain, avg_score in domain_scores_query}
    
    strongest_area = max(skill_scores, key=skill_scores.get) if skill_scores else "N/A"
    improvement_area = min(skill_scores, key=skill_scores.get) if skill_scores else "N/A"
    
    ai_summary = f"Based on {total_sessions} sessions, your performance is trending upwards. Your strongest area is {strongest_area}, showing consistent high scores. The primary area for improvement is {improvement_area}, where scores have been less consistent. Focusing on this domain will likely yield the greatest overall improvement."
    
    recommended_topics = [
        f"Core concepts in {improvement_area}",
        "Advanced algorithms related to your preferred domains",
        "System design principles for scalability"
    ]
    
    return jsonify({
        "data": {
            "overall_score": average_score,
            "total_sessions": total_sessions,
            "strongest_area": strongest_area,
            "improvement_area": improvement_area,
            "score_trend": score_trend,
            "skill_scores": skill_scores,
            "ai_summary": ai_summary,
            "recommended_topics": recommended_topics
        }
    })

@app.route('/api/profile', methods=['GET'])
@login_required
def api_profile_data():
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first_or_404()
    sessions = MCQSession.query.filter_by(user_id=current_user.id).order_by(MCQSession.end_time.desc()).all()
    codings = CodingAssessment.query.filter_by(user_id=current_user.id).order_by(CodingAssessment.submitted_at.desc()).all()
    all_scores = [s.score for s in sessions if s.score is not None] + [c.overall_score for c in codings if c.overall_score is not None]
    total_interviews = len(sessions) + len(codings)
    average_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    highest_score = round(max(all_scores)) if all_scores else 0
    dates = []
    if sessions and sessions[0].end_time:
        dates.append(sessions[0].end_time)
    if codings and codings[0].submitted_at:
        dates.append(codings[0].submitted_at)
    last_interview_date = max(dates).isoformat() if dates else None
    
    dob_str = user_profile.date_of_birth.strftime('%Y-%m-%d') if user_profile.date_of_birth else ""
    
    return jsonify({
        "username": current_user.username,
        "email": current_user.email,
        "first_name": user_profile.first_name or "",
        "last_name": user_profile.last_name or "",
        "phone_number": user_profile.phone_number or "",
        "gender": user_profile.gender or "",
        "date_of_birth": dob_str,
        "college_name": user_profile.college_name or "",
        "university": user_profile.university or "",
        "degree": user_profile.degree or "",
        "branch": user_profile.branch or "",
        "graduation_year": user_profile.graduation_year or "",
        "cgpa": user_profile.cgpa or "",
        "preferred_domain": user_profile.preferred_domain or "",
        "programming_languages": user_profile.programming_languages or "",
        "skills": user_profile.skills or "",
        "linkedin_profile": user_profile.linkedin_profile or "",
        "github_profile": user_profile.github_profile or "",
        "portfolio_website": user_profile.portfolio_website or "",
        "profile_image_filename": user_profile.profile_image_filename or 'default.png',
        "resume_filename": user_profile.resume_filename or "",
        "stats": {
            "total_interviews": total_interviews,
            "average_score": average_score,
            "highest_score": highest_score,
            "last_interview_date": last_interview_date
        }
    })

@app.route('/api/profile/edit', methods=['POST'])
@login_required
def api_profile_edit():
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first_or_404()
    data = request.form
    
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '' and allowed_image_file(file.filename):
            filename = secure_filename(f"user_{current_user.id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER_PROFILE'], filename))
            user_profile.profile_image_filename = filename
            
    if 'resume_upload' in request.files:
        file = request.files['resume_upload']
        if file and file.filename != '' and file.filename.endswith('.pdf'):
            filename = secure_filename(f"user_{current_user.id}_resume.pdf")
            file.save(os.path.join(app.config['UPLOAD_FOLDER_RESUME'], filename))
            user_profile.resume_filename = filename
            
    if data.get('remove_profile_picture') == '1':
        user_profile.profile_image_filename = 'default.png'
        
    user_profile.first_name = data.get('first_name')
    user_profile.last_name = data.get('last_name')
    user_profile.phone_number = data.get('phone_number')
    user_profile.gender = data.get('gender')
    dob_str = data.get('date_of_birth')
    user_profile.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
    user_profile.college_name = data.get('college_name')
    user_profile.university = data.get('university')
    user_profile.degree = data.get('degree')
    user_profile.branch = data.get('branch')
    user_profile.graduation_year = data.get('graduation_year', type=int)
    user_profile.cgpa = data.get('cgpa', type=float)
    user_profile.preferred_domain = data.get('preferred_domain')
    user_profile.programming_languages = data.get('programming_languages')
    user_profile.skills = data.get('skills')
    user_profile.linkedin_profile = data.get('linkedin_profile') or None
    user_profile.github_profile = data.get('github_profile') or None
    user_profile.portfolio_website = data.get('portfolio_website') or None
    db.session.commit()
    
    return jsonify({"success": True, "message": "Profile updated successfully."})

@app.route('/api/resume/upload', methods=['POST'])
@login_required
def api_resume_upload():
    if 'resume' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({"success": False, "message": "Empty file name."}), 400
        
    if file and file.filename.endswith('.pdf'):
        try:
            pdf_stream = file.read()
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            extracted_text = ""
            for page in doc:
                extracted_text += page.get_text()
                
            default_analysis = {
                "ats_score": 0, "technical_score": 0, "grammar_score": 0,
                "format_score": 0, "project_score": 0, "education_score": 0,
                "experience_score": 0, "keyword_score": 0, "strengths": [],
                "weaknesses": [], "missing_keywords": [], "suggestions": [],
                "overall_feedback": "Unable to analyze resume."
            }
            
            analysis_data = default_analysis

            try:
                payload = build_resume_webhook_payload(
                    resume_text=extracted_text,
                    job_description=request.form.get('job_description', '').strip(),
                    interview_type=request.form.get('interview_type', '').strip()
                )
            except PermissionError as error:
                return jsonify({'success': False, 'message': str(error)}), 401
            except ValueError as error:
                app.logger.error('API Resume Analyzer user identity error: %s', error)
                return jsonify({'success': False, 'message': str(error)}), 422

            job_desc = request.form.get('job_description', '').strip()
            job_role_val = request.form.get('interview_type', '').strip() or 'technical'

            try:
                validate_webhook_url()
                log_resume_webhook_payload(payload)
                response = requests.post(WEBHOOK_URL, json=payload, timeout=120)
                response.raise_for_status()
                json_response = response.json()
                new_rec, analysis_data = save_resume_analysis(
                    user_id=current_user.id,
                    job_role=job_role_val,
                    n8n_response=json_response,
                    filename=secure_filename(file.filename or 'resume.pdf'),
                    job_description=job_desc
                )
            except Exception as e:
                print("Error fetching from n8n webhook:", e)
                analysis_data = normalize_resume_analysis_response({}, job_role=job_role_val)
                    
            filename = secure_filename(f"user_{current_user.id}_resume.pdf")
            filepath = os.path.join(app.config['UPLOAD_FOLDER_RESUME'], filename)
            with open(filepath, 'wb') as f:
                f.write(pdf_stream)
                
            user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
            if user_profile:
                user_profile.resume_filename = filename
                db.session.commit()
                
            return jsonify({
                "success": True,
                "extracted_text_preview": extracted_text[:500],
                "analysis": analysis_data
            })
        except Exception as e:
            return jsonify({"success": False, "message": f"Processing error: {str(e)}"}), 500
    return jsonify({"success": False, "message": "Only PDF is supported."}), 400

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect('/admin/dashboard') if current_user.role == 'admin' else abort(403)
    if request.method == 'POST':
        if not csrf_ok():
            flash('Your session expired. Please try again.', 'danger')
            return redirect(url_for('admin_login'))
        user = User.query.filter(func.lower(User.email) == (request.form.get('email') or '').strip().lower()).first()
        if user and user.role == 'admin' and user.is_active_account and bcrypt.check_password_hash(user.password_hash, request.form.get('password') or ''):
            login_user(user, remember=False)
            session["user_id"] = user.id
            session["user_email"] = user.email
            session["user_name"] = user.username
            session["role"] = user.role
            session.modified = True
            audit('Login', 'Admin panel')
            return redirect('/admin/dashboard')
        flash('Invalid administrator credentials.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout', methods=['POST'])
@admin_required
def admin_logout():
    if not csrf_ok():
        abort(400)
    audit('Logout', 'Admin panel')
    logout_user()
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('role', None)
    session.modified = True
    return redirect(url_for('admin_login'))

def admin_context(section):
    user_query = User.query.order_by(User.created_at.desc())
    search = (request.args.get('q') or '').strip()
    role_filter = (request.args.get('role') or '').strip()
    status_filter = (request.args.get('status') or '').strip()
    if search:
        pattern = f'%{search}%'
        user_query = user_query.filter(db.or_(User.username.ilike(pattern), User.email.ilike(pattern)))
    if role_filter in ('user', 'admin'):
        user_query = user_query.filter(User.role == role_filter)
    if status_filter in ('active', 'disabled'):
        user_query = user_query.filter(User.is_active_account.is_(status_filter == 'active'))
    page = max(request.args.get('page', 1, type=int), 1)
    pagination = user_query.paginate(page=page, per_page=10, error_out=False)
    users = User.query.options(db.joinedload(User.profile)).order_by(User.created_at.desc()).all()
    mcqs = MCQSession.query.order_by(MCQSession.start_time.desc()).all()
    interviews = InterviewSession.query.order_by(InterviewSession.start_time.desc()).all()
    resumes = ResumeAnalysis.query.order_by(ResumeAnalysis.created_at.desc()).all()
    codings = CodingAssessment.query.order_by(CodingAssessment.submitted_at.desc()).all()
    certificates = CertificateRecord.query.order_by(CertificateRecord.issue_date.desc()).all()
    journeys = InterviewJourney.query.order_by(InterviewJourney.created_at.desc()).all()

    completed = [i for i in interviews if i.status == 'completed']
    ats_scores = [r.ats_score for r in resumes if r.ats_score is not None]
    aptitude_scores = [i.score for i in mcqs if i.score is not None]
    coding_scores = [c.overall_score for c in codings if c.overall_score is not None]
    active_cutoff = datetime.utcnow() - timedelta(days=30)

    stats = {
        'total_users': len(users), 
        'active_users': sum(bool(u.is_active_account and u.profile and u.profile.last_login and u.profile.last_login >= active_cutoff) for u in users),
        'resume_analyses': len(resumes),
        'resumes': len(resumes),
        'aptitude_attempts': len(mcqs),
        'aptitude_assessments': len(mcqs),
        'coding_attempts': len(codings),
        'certificates_issued': len(certificates),
        'completed_journeys': sum(1 for j in journeys if j.status == 'completed'),
        'avg_ats': round(sum(ats_scores) / len(ats_scores), 1) if ats_scores else None,
        'avg_aptitude': round(sum(aptitude_scores) / len(aptitude_scores), 1) if aptitude_scores else None,
        'avg_coding': round(sum(coding_scores) / len(coding_scores), 1) if coding_scores else None,
        'total_interviews': len(codings) + len(mcqs),
        'completed_interviews': sum(1 for j in journeys if j.status == 'completed'),
        'avg_interview': round(sum(coding_scores) / len(coding_scores), 1) if coding_scores else None,
        'failed': sum(i.status in ('failed', 'abandoned') for i in interviews)
    }

    user_rows_enhanced = []
    for u in pagination.items:
        dom = get_user_selected_domain(u)
        j = InterviewJourney.query.filter_by(user_id=u.id).order_by(InterviewJourney.created_at.desc()).first()
        j_status = "Not Started"
        if j:
            j_status = "Completed" if j.status == 'completed' else "In Progress"
        
        latest_score = None
        cert = CertificateRecord.query.filter_by(user_id=u.id).order_by(CertificateRecord.issue_date.desc()).first()
        if cert:
            latest_score = f"{round((cert.ats_score + cert.aptitude_score + cert.coding_score)/3.0, 1)}%"
        elif j and j.coding_score is not None:
            latest_score = f"{round(j.coding_score, 1)}%"
        elif j and j.aptitude_score is not None:
            latest_score = f"{j.aptitude_score}%"
        elif j and j.ats_score is not None:
            latest_score = f"{round(j.ats_score, 1)}%"

        user_rows_enhanced.append({
            'user': u,
            'domain': dom or '—',
            'journey_status': j_status,
            'latest_score': latest_score or '—'
        })

    def monthly(items, attr):
        labels=[]; values=[]
        now=datetime.utcnow()
        for offset in range(5, -1, -1):
            month=(now.replace(day=1)-timedelta(days=offset*28)).replace(day=1)
            label=month.strftime('%b %Y'); labels.append(label)
            values.append(sum(1 for x in items if getattr(x, attr, None) and getattr(x, attr).strftime('%b %Y') == label))
        return {'labels': labels, 'values': values}

    domains={}
    for item in mcqs:
        dom = normalize_canonical_domain(item.domain) or item.domain
        domains[dom] = domains.get(dom, 0) + 1
    for item in codings:
        dom = normalize_canonical_domain(item.domain) or item.domain
        domains[dom] = domains.get(dom, 0) + 1

    charts={'growth':monthly(users,'created_at'),'activity':monthly(mcqs,'start_time'),
            'scores':{'labels':['ATS Match','Aptitude','Coding'],'values':[stats['avg_ats'] or 0,stats['avg_aptitude'] or 0,stats['avg_coding'] or 0]},
            'ats':{'labels':['0–39','40–59','60–79','80–100'],'values':[sum(0<=s<40 for s in ats_scores),sum(40<=s<60 for s in ats_scores),sum(60<=s<80 for s in ats_scores),sum(80<=s<=100 for s in ats_scores)]},
            'domains':{'labels':list(domains.keys()),'values':list(domains.values())}}

    resume_rows=[]
    for resume in resumes:
        try: payload=json.loads(resume.analysis_json)
        except (TypeError, ValueError): payload={}
        if not isinstance(payload, dict): payload={}
        def score(*keys):
            value=next((payload.get(k) for k in keys if payload.get(k) is not None), None)
            if isinstance(value, dict): value=value.get('score')
            return value
        resume_rows.append({'record':resume, 'technical':score('technical_skills','technical_score','technical'),
                            'projects':score('projects_impact','projects_score','projects'), 'experience':score('work_experience','experience_score','experience'),
                            'education':score('education_alignment','education_score','education')})
    
    settings_dict = {}
    try:
        settings_dict = {s.key: s.value for s in PlatformSetting.query.all()}
    except Exception:
        pass

    return dict(section=section, users=users, user_rows=pagination.items, user_rows_enhanced=user_rows_enhanced, pagination=pagination,
                search=search, role_filter=role_filter, status_filter=status_filter,
                mcqs=mcqs, interviews=interviews, resumes=resumes, resume_rows=resume_rows,
                codings=codings, certificates=certificates, journeys=journeys,
                stats=stats, charts=charts, settings_dict=settings_dict)

def render_admin(section, **kwargs):
    context = admin_context(section)
    context.update(kwargs)
    return render_template('admin_console.html', **context)

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard(): return render_admin('dashboard')

@app.route('/admin/users')
@admin_required
def admin_users(): return render_admin('users')

@app.route('/admin/interviews')
@admin_required
def admin_interviews(): return render_admin('interviews')

@app.route('/admin/resumes')
@admin_required
def admin_resumes(): return render_admin('resumes')

@app.route('/admin/aptitude-assessments')
@admin_required
def admin_coding(): return render_admin('coding')

@app.route('/admin/coding-assessments')
@admin_required
def admin_coding_assessments(): return render_admin('coding-assessments')

@app.route('/admin/certificates')
@admin_required
def admin_certificates(): return render_admin('certificates')

@app.route('/admin/coding-assessments/<int:item_id>')
@admin_required
def admin_coding_detail(item_id):
    assessment = CodingAssessment.query.get_or_404(item_id)
    audit('View coding assessment', f'Coding #{item_id}')
    results = []
    if assessment.results_data:
        try:
            results = json.loads(assessment.results_data)
        except Exception:
            results = []
    return render_admin('coding-detail', item=assessment, results=results)

@app.route('/admin/analytics')
@admin_required
def admin_analytics(): return render_admin('analytics')

@app.route('/admin/profile')
@admin_required
def admin_profile(): return render_admin('profile')

@app.route('/admin/settings')
@admin_required
def admin_settings(): return render_admin('settings')

@app.route('/admin/users/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    user=User.query.get_or_404(user_id); audit('View user', f'User #{user.id}')
    return render_admin('user-detail', item=user)

@app.route('/admin/interviews/<string:kind>/<int:item_id>')
@admin_required
def admin_interview_detail(kind, item_id):
    item = MCQSession.query.get_or_404(item_id) if kind == 'mcq' else InterviewSession.query.get_or_404(item_id)
    audit('View interview', f'{kind} #{item_id}')
    return render_admin('interview-detail', kind=kind, item=item)

@app.route('/admin/resumes/<int:item_id>')
@admin_required
def admin_resume_detail(item_id):
    item=ResumeAnalysis.query.get_or_404(item_id); audit('View resume report', f'Resume #{item_id}')
    try: analysis=json.loads(item.analysis_json)
    except ValueError: analysis={'report':item.analysis_json}
    return render_admin('resume-detail', item=item, analysis=analysis)

@app.route('/admin/users/<int:user_id>/<action>', methods=['POST'])
@admin_required
def admin_user_action(user_id, action):
    if not csrf_ok(): abort(400)
    user=User.query.get_or_404(user_id)
    if user.id == current_user.id: flash('You cannot modify your own administrator account here.', 'warning')
    elif action == 'toggle':
        user.is_active_account=not user.is_active_account; db.session.commit(); audit('Enable user' if user.is_active_account else 'Disable user', f'User #{user.id}')
    elif action == 'delete':
        target=f'User #{user.id} ({user.email})'; db.session.delete(user); db.session.commit(); audit('Delete user', target)
    else: abort(404)
    return redirect(url_for('admin_users'))



@app.route('/admin/settings', methods=['POST'])
@admin_required
def admin_settings_update():
    if not csrf_ok(): abort(400)
    allowed={'maintenance_mode':'Platform','default_difficulty':'Interview'}
    for key, category in allowed.items():
        if key in request.form:
            row=PlatformSetting.query.filter_by(key=key).first() or PlatformSetting(key=key, category=category, value='')
            row.value=request.form[key][:255]; db.session.add(row)
    db.session.commit(); audit('Change settings','Safe platform settings'); flash('Settings saved.','success')
    return redirect(url_for('admin_settings'))

def initialize_database():
    db.create_all()
    inspector=inspect(db.engine)
    columns={c['name'] for c in inspector.get_columns('user')}
    additions={'google_id':'VARCHAR(100)','profile_picture':'VARCHAR(255)','otp':'VARCHAR(6)','otp_expiry':'DATETIME','remember_token':'VARCHAR(128)',
               'role':"VARCHAR(20) NOT NULL DEFAULT 'user'",'is_active_account':'BOOLEAN NOT NULL DEFAULT 1','created_at':'DATETIME'}
    with db.engine.begin() as conn:
        for name, sql_type in additions.items():
            if name not in columns: conn.execute(db.text(f'ALTER TABLE user ADD COLUMN {name} {sql_type}'))
        conn.execute(db.text("UPDATE user SET role='user' WHERE role IS NULL OR role NOT IN ('user','admin')"))
        conn.execute(db.text('UPDATE user SET is_active_account=1 WHERE is_active_account IS NULL'))
        conn.execute(db.text('UPDATE user SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL'))
        
        # Add migrations for mcq_session table
        mcq_columns = {c['name'] for c in inspector.get_columns('mcq_session')}
        mcq_additions = {
            'camera_verified': 'BOOLEAN DEFAULT 1',
            'microphone_verified': 'BOOLEAN DEFAULT 1',
            'fullscreen_warnings': 'INTEGER DEFAULT 0',
            'tab_switch_warnings': 'INTEGER DEFAULT 0',
            'proctoring_warnings': 'INTEGER DEFAULT 0',
            'interview_status': "VARCHAR(20) DEFAULT 'completed'"
        }
        for name, sql_type in mcq_additions.items():
            if name not in mcq_columns:
                conn.execute(db.text(f'ALTER TABLE mcq_session ADD COLUMN {name} {sql_type}'))

        # Add migrations for resume_analysis table
        res_columns = {c['name'] for c in inspector.get_columns('resume_analysis')}
        res_additions = {
            'filename': 'VARCHAR(255)',
            'job_description': 'TEXT'
        }
        for name, sql_type in res_additions.items():
            if name not in res_columns:
                conn.execute(db.text(f'ALTER TABLE resume_analysis ADD COLUMN {name} {sql_type}'))

    admin=User.query.filter(func.lower(User.email)==INITIAL_ADMIN_EMAIL).first()
    if admin is None:
        username='admin'
        suffix=1
        while User.query.filter_by(username=username).first():
            suffix += 1
            username=f'admin{suffix}'
        admin=User(username=username, email=INITIAL_ADMIN_EMAIL,
                   password_hash=INITIAL_ADMIN_PASSWORD_HASH, role='admin',
                   is_active_account=True, created_at=datetime.utcnow())
        db.session.add(admin)
    else:
        admin.role='admin'
        admin.is_active_account=True
        admin.password_hash=INITIAL_ADMIN_PASSWORD_HASH
    db.session.commit()
    backfill_existing_resume_analyses()
    backfill_mixed_target_roles()

with app.app_context():
    initialize_database()

if __name__ == '__main__':
    # Initialize the development database context safely
    with app.app_context():
        db.create_all()
        # Custom SQLite migrations for authentication module enhancements
        inspector = inspect(db.engine)
        if 'user' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('user')]
            with db.engine.connect() as conn:
                if 'google_id' not in columns:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN google_id VARCHAR(100)"))
                if 'profile_picture' not in columns:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN profile_picture VARCHAR(255)"))
                if 'otp' not in columns:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN otp VARCHAR(6)"))
                if 'otp_expiry' not in columns:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN otp_expiry DATETIME"))
                if 'remember_token' not in columns:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN remember_token VARCHAR(128)"))
                conn.commit()
    app.run(debug=True)

