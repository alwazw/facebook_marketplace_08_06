from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class AutomationRun(db.Model):
    __tablename__ = 'automation_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    facebook_account_id = db.Column(db.Integer, db.ForeignKey('facebook_accounts.id'), nullable=False)
    run_type = db.Column(db.String(50), nullable=False)  # manual, scheduled, auto
    status = db.Column(db.String(50), nullable=False)  # running, completed, failed, cancelled
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    
    # Metrics
    conversations_checked = db.Column(db.Integer, default=0, nullable=False)
    new_messages_found = db.Column(db.Integer, default=0, nullable=False)
    messages_processed = db.Column(db.Integer, default=0, nullable=False)
    responses_sent = db.Column(db.Integer, default=0, nullable=False)
    errors_encountered = db.Column(db.Integer, default=0, nullable=False)
    
    # Performance metrics
    avg_processing_time_per_message = db.Column(db.Float, nullable=True)
    success_rate = db.Column(db.Float, nullable=True)
    
    # Error tracking
    error_details = db.Column(db.Text, nullable=True)  # JSON string
    warnings = db.Column(db.Text, nullable=True)  # JSON string
    
    # Additional data
    run_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional metrics
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<AutomationRun {self.id} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'facebook_account_id': self.facebook_account_id,
            'run_type': self.run_type,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'conversations_checked': self.conversations_checked,
            'new_messages_found': self.new_messages_found,
            'messages_processed': self.messages_processed,
            'responses_sent': self.responses_sent,
            'errors_encountered': self.errors_encountered,
            'avg_processing_time_per_message': self.avg_processing_time_per_message,
            'success_rate': self.success_rate,
            'error_details': self.get_error_details(),
            'warnings': self.get_warnings(),
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def set_error_details(self, errors):
        """Store error details as JSON string"""
        self.error_details = json.dumps(errors) if errors else None
    
    def get_error_details(self):
        """Retrieve error details from JSON string"""
        return json.loads(self.error_details) if self.error_details else []
    
    def set_warnings(self, warnings):
        """Store warnings as JSON string"""
        self.warnings = json.dumps(warnings) if warnings else None
    
    def get_warnings(self):
        """Retrieve warnings from JSON string"""
        return json.loads(self.warnings) if self.warnings else []
    
    def set_metadata(self, data):
        """Store metadata as JSON string"""
        self.run_metadata = json.dumps(data) if data else None
    
    def get_metadata(self):
        """Retrieve metadata from JSON string"""
        return json.loads(self.run_metadata) if self.run_metadata else {}
    
    def start_run(self):
        """Mark run as started"""
        self.status = 'running'
        self.start_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def complete_run(self):
        """Mark run as completed and calculate metrics"""
        self.status = 'completed'
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        # Calculate success rate
        if self.messages_processed > 0:
            self.success_rate = (self.responses_sent / self.messages_processed) * 100
        else:
            self.success_rate = 100.0 if self.errors_encountered == 0 else 0.0
        
        self.updated_at = datetime.utcnow()
    
    def fail_run(self, error_message=None):
        """Mark run as failed"""
        self.status = 'failed'
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        if error_message:
            current_errors = self.get_error_details()
            current_errors.append({
                'timestamp': datetime.utcnow().isoformat(),
                'error': error_message
            })
            self.set_error_details(current_errors)
        
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error_message, error_type='general'):
        """Add an error to the run"""
        self.errors_encountered += 1
        current_errors = self.get_error_details()
        current_errors.append({
            'timestamp': datetime.utcnow().isoformat(),
            'type': error_type,
            'message': error_message
        })
        self.set_error_details(current_errors)
        self.updated_at = datetime.utcnow()
    
    def add_warning(self, warning_message, warning_type='general'):
        """Add a warning to the run"""
        current_warnings = self.get_warnings()
        current_warnings.append({
            'timestamp': datetime.utcnow().isoformat(),
            'type': warning_type,
            'message': warning_message
        })
        self.set_warnings(current_warnings)
        self.updated_at = datetime.utcnow()


class SystemMetric(db.Model):
    __tablename__ = 'system_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # counter, gauge, histogram
    tags = db.Column(db.String(500), nullable=True)  # JSON string for tags
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<SystemMetric {self.metric_name}: {self.metric_value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_type': self.metric_type,
            'tags': self.get_tags(),
            'timestamp': self.timestamp.isoformat()
        }
    
    def get_tags(self):
        """Get tags as dictionary"""
        return json.loads(self.tags) if self.tags else {}
    
    def set_tags(self, tags_dict):
        """Set tags from dictionary"""
        self.tags = json.dumps(tags_dict) if tags_dict else None


class ValidationLog(db.Model):
    __tablename__ = 'validation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    validation_type = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)  # account, conversation, message, etc.
    entity_id = db.Column(db.Integer, nullable=True)
    validation_status = db.Column(db.String(50), nullable=False)  # passed, failed, warning
    validation_message = db.Column(db.Text, nullable=True)
    validation_data = db.Column(db.Text, nullable=True)  # JSON string
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<ValidationLog {self.validation_type}: {self.validation_status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'validation_type': self.validation_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'validation_status': self.validation_status,
            'validation_message': self.validation_message,
            'validation_data': self.get_validation_data(),
            'timestamp': self.timestamp.isoformat()
        }
    
    def get_validation_data(self):
        """Get validation data as dictionary"""
        return json.loads(self.validation_data) if self.validation_data else {}
    
    def set_validation_data(self, data):
        """Set validation data from dictionary"""
        self.validation_data = json.dumps(data) if data else None

