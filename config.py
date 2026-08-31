"""
Flixora AI Sales Automation Agent — Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    
    # Database
    _database_url = os.environ.get('DATABASE_URL')
    if _database_url and _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = _database_url or f'sqlite:///{os.path.join(BASE_DIR, "instance", "flixora.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 7  # 7 days
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '')

    # Test Mode
    TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() in ('true', '1', 'yes')

    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
    ALLOWED_DOC_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md'}

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.path.join(BASE_DIR, 'logs')

    # Default Admin
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@flixora.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

    # Rate Limiting
    LOGIN_RATE_LIMIT = 5  # attempts per window
    LOGIN_RATE_WINDOW = 300  # 5 minutes
    DISABLE_RATE_LIMIT = False

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # Lead Discovery
    DEFAULT_DAILY_LEAD_TARGET = 20


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_RATE_LIMIT = 100
    DISABLE_RATE_LIMIT = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
