from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO

# Database ORM instance
db = SQLAlchemy()

# Real-time WebSocket manager
socketio = SocketIO(cors_allowed_origins="*", async_mode=None)

# Authentication & Session manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
