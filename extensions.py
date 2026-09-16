"""Central place for Flask extension instances to avoid circular imports."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login_select"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
