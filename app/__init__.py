from flask import Flask, render_template
from config import config
from app.extensions import db, socketio, login_manager


def create_app(config_name='default'):
    """Application factory for the Real-Time Chat Application."""
    flask_app = Flask(__name__)
    flask_app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(flask_app)
    socketio.init_app(flask_app)
    login_manager.init_app(flask_app)

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.chat.routes import chat_bp

    flask_app.register_blueprint(auth_bp, url_prefix='/auth')
    flask_app.register_blueprint(chat_bp, url_prefix='')

    # Bind Socket.IO events and initialize schema
    with flask_app.app_context():
        from app.chat import events as _chat_events  # noqa: F401
        db.create_all()

    # Security Headers
    @flask_app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Global Error Handlers
    @flask_app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', error_code=404, error_message='Page Not Found'), 404

    @flask_app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template('base.html', error_code=500, error_message='Internal Server Error'), 500

    return flask_app
