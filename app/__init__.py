
from flask import Flask, render_template
from config import config
from app.extensions import db, socketio, login_manager


def create_app(config_name='default'):
    """Application factory for the Real-Time Chat Application."""

    flask_app = Flask(__name__)
    flask_app.config.from_object(config[config_name])

    db.init_app(flask_app)
    login_manager.init_app(flask_app)
    socketio.init_app(flask_app)

    from app.auth.routes import auth_bp
    from app.chat.routes import chat_bp
    from app.chat import events

    # Register Socket.IO handlers for every application instance
    socket_handlers = {
        'connect': events.handle_connect,
        'disconnect': events.handle_disconnect,
        'send_direct_message': events.handle_send_direct_message,
        'send_room_message': events.handle_send_room_message,
        'join_room_event': events.handle_join_room_event,
        'leave_room_event': events.handle_leave_room_event,
        'typing_indicator': events.handle_typing_indicator,
        'mark_read_event': events.handle_mark_read_event,
    }

    for event_name, handler in socket_handlers.items():
        socketio.on_event(event_name, handler)

    flask_app.register_blueprint(auth_bp, url_prefix='/auth')
    flask_app.register_blueprint(chat_bp, url_prefix='')

    with flask_app.app_context():
        db.create_all()

    @flask_app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    @flask_app.errorhandler(404)
    def page_not_found(e):
        return render_template(
            'base.html',
            error_code=404,
            error_message='Page Not Found'
        ), 404

    @flask_app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template(
            'base.html',
            error_code=500,
            error_message='Internal Server Error'
        ), 500

    return flask_app
