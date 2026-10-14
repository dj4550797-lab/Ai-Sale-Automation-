"""
Flixora AI Sales Automation Agent — Flask Extensions

All extension instances are created here and initialized in the app factory.
This avoids circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

# Database
db = SQLAlchemy()

# Authentication
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# CSRF Protection
csrf = CSRFProtect()

# Database Migrations
migrate = Migrate()
