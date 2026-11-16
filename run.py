import os
from app import create_app
from app.extensions import socketio

# Determine configuration environment
env_config = os.getenv('FLASK_CONFIG', 'development')
app = create_app(env_config)

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

    print(f"============================================================")
    print(f"  ChatPulse — Real-Time Chat Application (Flask-SocketIO)  ")
    print(f"  Running on: http://{host}:{port}")
    print(f"  Environment: {env_config}")
    print(f"============================================================")

    # socketio.run provides compatible WebSocket serving on Windows
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True
    )
