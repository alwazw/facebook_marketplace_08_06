from sqlalchemy import Numeric
from datetime import datetime
from src.models.facebook_account import db

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    facebook_account_id = db.Column(db.Integer, db.ForeignKey('facebook_accounts.id'), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_profile_url = db.Column(db.String(500), nullable=True)
    marketplace_item_id = db.Column(db.String(255), nullable=True)
    marketplace_item_title = db.Column(db.String(500), nullable=True)
    marketplace_item_price = db.Column(Numeric(10, 2), nullable=True)
    status = db.Column(db.String(50), default='active', nullable=False)  # active, closed, archived
    priority = db.Column(db.String(20), default='normal', nullable=False)  # low, normal, high, urgent
    last_message_time = db.Column(db.DateTime, nullable=True)
    last_customer_message_time = db.Column(db.DateTime, nullable=True)
    last_bot_response_time = db.Column(db.DateTime, nullable=True)
    message_count = db.Column(db.Integer, default=0, nullable=False)
    customer_message_count = db.Column(db.Integer, default=0, nullable=False)
    bot_response_count = db.Column(db.Integer, default=0, nullable=False)
    unread_count = db.Column(db.Integer, default=0, nullable=False)
    response_time_avg_minutes = db.Column(db.Float, nullable=True)
    conversation_rating = db.Column(db.Integer, nullable=True)  # 1-5 rating
    tags = db.Column(db.String(500), nullable=True)  # comma-separated tags
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Conversation {self.id} - {self.customer_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'facebook_account_id': self.facebook_account_id,
            'customer_name': self.customer_name,
            'customer_profile_url': self.customer_profile_url,
            'marketplace_item_id': self.marketplace_item_id,
            'marketplace_item_title': self.marketplace_item_title,
            'marketplace_item_price': float(self.marketplace_item_price) if self.marketplace_item_price else None,
            'status': self.status,
            'priority': self.priority,
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'last_customer_message_time': self.last_customer_message_time.isoformat() if self.last_customer_message_time else None,
            'last_bot_response_time': self.last_bot_response_time.isoformat() if self.last_bot_response_time else None,
            'message_count': self.message_count,
            'customer_message_count': self.customer_message_count,
            'bot_response_count': self.bot_response_count,
            'unread_count': self.unread_count,
            'response_time_avg_minutes': self.response_time_avg_minutes,
            'conversation_rating': self.conversation_rating,
            'tags': self.tags.split(',') if self.tags else [],
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def update_message_stats(self):
        """Update conversation statistics based on messages"""
        from src.models.message import Message
        
        # Count messages
        self.message_count = len(self.messages)
        self.customer_message_count = len([m for m in self.messages if m.is_from_customer])
        self.bot_response_count = len([m for m in self.messages if not m.is_from_customer])
        
        # Update last message times
        if self.messages:
            self.last_message_time = max(m.timestamp for m in self.messages)
            
            customer_messages = [m for m in self.messages if m.is_from_customer]
            if customer_messages:
                self.last_customer_message_time = max(m.timestamp for m in customer_messages)
            
            bot_messages = [m for m in self.messages if not m.is_from_customer]
            if bot_messages:
                self.last_bot_response_time = max(m.timestamp for m in bot_messages)
        
        # Calculate unread count (customer messages without bot responses after them)
        self.unread_count = len([m for m in self.messages if m.is_from_customer and not m.is_processed])
        
        # Calculate average response time
        response_times = []
        customer_msgs = sorted([m for m in self.messages if m.is_from_customer], key=lambda x: x.timestamp)
        bot_msgs = sorted([m for m in self.messages if not m.is_from_customer], key=lambda x: x.timestamp)
        
        for customer_msg in customer_msgs:
            # Find next bot response after this customer message
            next_bot_response = next((b for b in bot_msgs if b.timestamp > customer_msg.timestamp), None)
            if next_bot_response:
                response_time = (next_bot_response.timestamp - customer_msg.timestamp).total_seconds() / 60
                response_times.append(response_time)
        
        if response_times:
            self.response_time_avg_minutes = sum(response_times) / len(response_times)
        
        self.updated_at = datetime.utcnow()
    
    def add_tag(self, tag):
        """Add a tag to the conversation"""
        current_tags = self.tags.split(',') if self.tags else []
        if tag not in current_tags:
            current_tags.append(tag)
            self.tags = ','.join(current_tags)
    
    def remove_tag(self, tag):
        """Remove a tag from the conversation"""
        current_tags = self.tags.split(',') if self.tags else []
        if tag in current_tags:
            current_tags.remove(tag)
            self.tags = ','.join(current_tags) if current_tags else None

