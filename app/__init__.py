from flask import Flask
from flask_socketio import SocketIO
import logging

# Configure logging to help debug WebSocket issues
logging.basicConfig(level=logging.INFO)

socketio = SocketIO(
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    async_mode='threading'
)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret!'
    
    # Register routes
    from .routes import main
    app.register_blueprint(main)

    # Initialize SocketIO with the app
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Add WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        print(f"🔌 Client connected: {request.sid if 'request' in globals() else 'unknown'}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"🔌 Client disconnected: {request.sid if 'request' in globals() else 'unknown'}")
    
    print("✅ Flask app created with SocketIO initialized")
    return app