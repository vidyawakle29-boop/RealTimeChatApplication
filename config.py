import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

basedir = Path(__file__).resolve().parent

# Load local .env if present
load_dotenv(basedir / '.env')


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-super-secret-key-change-in-prod-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session & Security hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max request payload
    
    # Real-time WebSocket settings
    SOCKETIO_PING_TIMEOUT = 20
    SOCKETIO_PING_INTERVAL = 10


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    instance_dir = basedir / 'instance'
    instance_dir.mkdir(exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{instance_dir / 'chat.db'}"
    )


class TestingConfig(Config):
    """Testing configuration with shared in-memory SQLite database."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False}
    }
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-key-for-automated-suites'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SESSION_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
