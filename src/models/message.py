from datetime import datetime
import json
from src.models.facebook_account import db

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    is_from_customer = db.Column(db.Boolean, nullable=False)
    is_processed = db.Column(db.Boolean, default=False, nullable=False)
    is_automated_response = db.Column(db.Boolean, default=False, nullable=False)
    message_type = db.Column(db.String(100), nullable=True)  # price_inquiry, availability, general, etc.
    classification_confidence = db.Column(db.Float, nullable=True)
    template_used = db.Column(db.String(100), nullable=True)
    response_generated = db.Column(db.Text, nullable=True)
    response_sent = db.Column(db.Boolean, default=False, nullable=False)
    response_sent_at = db.Column(db.DateTime, nullable=True)
    processing_time_seconds = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    message_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Message {self.id} - {"Customer" if self.is_from_customer else "Bot"}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'message_text': self.message_text,
            'is_from_customer': self.is_from_customer,
            'is_processed': self.is_processed,
            'is_automated_response': self.is_automated_response,
            'message_type': self.message_type,
            'classification_confidence': self.classification_confidence,
            'template_used': self.template_used,
            'response_generated': self.response_generated,
            'response_sent': self.response_sent,
            'response_sent_at': self.response_sent_at.isoformat() if self.response_sent_at else None,
            'processing_time_seconds': self.processing_time_seconds,
            'error_message': self.error_message,
            'metadata': self.get_metadata(),
            'timestamp': self.timestamp.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def set_metadata(self, data):
        """Store metadata as JSON string"""
        self.message_metadata = json.dumps(data) if data else None
    
    def get_metadata(self):
        """Retrieve metadata from JSON string"""
        return json.loads(self.message_metadata) if self.message_metadata else {}
    
    def classify_message(self):
        """Classify the message type based on content"""
        text = self.message_text.lower()
        
        # Price-related keywords
        price_keywords = ['price', 'cost', 'how much', 'expensive', 'cheap', 'dollar', '$', 'money', 'pay']
        if any(keyword in text for keyword in price_keywords):
            self.message_type = 'price_inquiry'
            self.classification_confidence = 0.8
            return
        
        # Availability keywords
        availability_keywords = ['available', 'still have', 'in stock', 'sold', 'buy', 'purchase', 'get']
        if any(keyword in text for keyword in availability_keywords):
            self.message_type = 'availability_check'
            self.classification_confidence = 0.8
            return
        
        # Location/pickup keywords
        location_keywords = ['pickup', 'location', 'where', 'address', 'meet', 'come']
        if any(keyword in text for keyword in location_keywords):
            self.message_type = 'location_inquiry'
            self.classification_confidence = 0.7
            return
        
        # Condition/details keywords
        condition_keywords = ['condition', 'quality', 'new', 'used', 'broken', 'work', 'function']
        if any(keyword in text for keyword in condition_keywords):
            self.message_type = 'condition_inquiry'
            self.classification_confidence = 0.7
            return
        
        # Greeting/initial contact
        greeting_keywords = ['hi', 'hello', 'hey', 'interested', 'want', 'like']
        if any(keyword in text for keyword in greeting_keywords):
            self.message_type = 'initial_contact'
            self.classification_confidence = 0.6
            return
        
        # Default to general inquiry
        self.message_type = 'general_inquiry'
        self.classification_confidence = 0.5
    
    def mark_processed(self, template_used=None, response_generated=None, processing_time=None):
        """Mark message as processed"""
        self.is_processed = True
        self.processed_at = datetime.utcnow()
        if template_used:
            self.template_used = template_used
        if response_generated:
            self.response_generated = response_generated
        if processing_time:
            self.processing_time_seconds = processing_time
        self.updated_at = datetime.utcnow()
    
    def mark_response_sent(self):
        """Mark response as sent"""
        self.response_sent = True
        self.response_sent_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class MessageTemplate(db.Model):
    __tablename__ = 'message_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    message_type = db.Column(db.String(100), nullable=False)
    template_text = db.Column(db.Text, nullable=False)
    variables = db.Column(db.Text, nullable=True)  # JSON array of variable names
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    success_rate = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<MessageTemplate {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'message_type': self.message_type,
            'template_text': self.template_text,
            'variables': self.get_variables(),
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'success_rate': self.success_rate,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_variables(self):
        """Get template variables as list"""
        return json.loads(self.variables) if self.variables else []
    
    def set_variables(self, variables_list):
        """Set template variables from list"""
        self.variables = json.dumps(variables_list) if variables_list else None
    
    def render(self, **kwargs):
        """Render template with provided variables"""
        template_text = self.template_text
        for key, value in kwargs.items():
            template_text = template_text.replace(f'{{{key}}}', str(value))
        return template_text
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.updated_at = datetime.utcnow()

