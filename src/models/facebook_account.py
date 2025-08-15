from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class FacebookAccount(db.Model):
    __tablename__ = 'facebook_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)  # Encrypt in a real-world app
    display_name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    lock_reason = db.Column(db.String(500), nullable=True)
    last_used = db.Column(db.DateTime, nullable=True)
    login_attempts = db.Column(db.Integer, default=0, nullable=False)
    successful_logins = db.Column(db.Integer, default=0, nullable=False)
    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    session_data = db.Column(db.Text, nullable=True)  # JSON string for browser session
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='account', lazy=True, cascade='all, delete-orphan')
    automation_runs = db.relationship('AutomationRun', backref='account', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FacebookAccount {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'is_locked': self.is_locked,
            'lock_reason': self.lock_reason,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'login_attempts': self.login_attempts,
            'successful_logins': self.successful_logins,
            'failed_logins': self.failed_logins,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def set_session_data(self, data):
        """Store session data as JSON string"""
        self.session_data = json.dumps(data) if data else None
    
    def get_session_data(self):
        """Retrieve session data from JSON string"""
        return json.loads(self.session_data) if self.session_data else None
    
    def lock_account(self, reason):
        """Lock account with reason"""
        self.is_locked = True
        self.lock_reason = reason
        self.updated_at = datetime.utcnow()
    
    def unlock_account(self):
        """Unlock account"""
        self.is_locked = False
        self.lock_reason = None
        self.updated_at = datetime.utcnow()
    
    def record_login_attempt(self, success=True):
        """Record login attempt"""
        self.login_attempts += 1
        if success:
            self.successful_logins += 1
            self.last_used = datetime.utcnow()
        else:
            self.failed_logins += 1
        self.updated_at = datetime.utcnow()

