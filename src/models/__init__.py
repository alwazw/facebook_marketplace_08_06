from flask_sqlalchemy import SQLAlchemy

# Import all models to ensure they are registered with SQLAlchemy
from src.models.facebook_account import FacebookAccount, db as facebook_db
from src.models.conversation import Conversation, db as conversation_db
from src.models.message import Message, MessageTemplate, db as message_db
from src.models.automation_run import AutomationRun, SystemMetric, ValidationLog, db as automation_db
from src.models.user import User, db as user_db

# Use the same db instance across all models
db = user_db

# Make sure all models use the same db instance
facebook_db.Model = db.Model
conversation_db.Model = db.Model
message_db.Model = db.Model
automation_db.Model = db.Model

__all__ = [
    'db',
    'FacebookAccount',
    'Conversation', 
    'Message',
    'MessageTemplate',
    'AutomationRun',
    'SystemMetric',
    'ValidationLog',
    'User'
]

