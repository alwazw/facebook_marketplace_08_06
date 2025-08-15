import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models import db
from src.routes.user import user_bp
from src.routes.automation import automation_bp
from src.routes.analytics import analytics_bp
from src.routes.dashboard import dashboard_bp
from src.routes.validation import validation_bp
from src.routes.tasks import tasks_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'facebook_marketplace_secret_key_2025'

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(automation_bp, url_prefix='/api/automation')
app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(validation_bp, url_prefix='/api/validation')
app.register_blueprint(tasks_bp, url_prefix='/api/tasks')

# Database configuration
database_dir = os.path.join(os.path.dirname(__file__), 'database')
os.makedirs(database_dir, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(database_dir, 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create all tables
with app.app_context():
    db.create_all()
    print("Database tables created successfully")
    
    # Seed database with sample data
    from src.services.data_seeder import seed_database
    try:
        seed_database()
        print("Sample data seeded successfully")
    except Exception as e:
        print(f"Error seeding data: {e}")
        # Continue anyway

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    # Initialize and start task manager
    from src.services.task_manager import get_task_manager
    task_manager = get_task_manager()
    task_manager.start()
    
    print("Facebook Marketplace Automation System started successfully!")
    print(f"Dashboard available at: http://0.0.0.0:5000")
    print(f"API documentation available at: http://0.0.0.0:5000/api")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
