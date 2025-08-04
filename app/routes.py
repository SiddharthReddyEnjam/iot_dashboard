from flask import Blueprint, render_template, jsonify, request
from .data_store import latest_data, history, get_decimal_coordinates
from . import config
import json

main = Blueprint('main', __name__)

@main.route("/")
def dashboard():
    """Serve the main dashboard"""
    return render_template("dashboard.html")

@main.route("/api/current")
def get_current_data():
    """Get current sensor readings"""
    lat_decimal, lon_decimal = get_decimal_coordinates()
    
    return jsonify({
        **latest_data,
        "lat_decimal": lat_decimal,
        "lon_decimal": lon_decimal,
        "source": "mock" if config.USE_MOCK else "device",
        "status": "active"
    })

@main.route("/api/history")
def get_history():
    """Get historical data for charts"""
    # Convert deques to lists for JSON serialization
    history_data = {}
    for key, values in history.items():
        history_data[key] = list(values)
    
    return jsonify(history_data)

@main.route("/api/config")
def get_config():
    """Get current configuration"""
    return jsonify({
        "use_mock": config.USE_MOCK,
        "serial_port": config.SERIAL_PORT,
        "baud_rate": config.BAUD_RATE,
        "max_chart_points": config.MAX_CHART_POINTS,
        "update_frequency": config.UPDATE_FREQUENCY
    })

@main.route("/api/config", methods=['POST'])
def update_config():
    """Update configuration (for toggling mock/real mode)"""
    data = request.get_json()
    
    if 'use_mock' in data:
        old_mode = config.USE_MOCK
        config.USE_MOCK = data['use_mock']
        
        # Restart the data reader with new mode
        from .serial_reader import stop_reader, start_reader
        from . import socketio
        
        print(f"🔄 Switching from {'mock' if old_mode else 'device'} to {'mock' if config.USE_MOCK else 'device'} mode")
        
        stop_reader()
        start_reader(socketio)
        
        return jsonify({
            "status": "success", 
            "message": f"Switched to {'mock' if config.USE_MOCK else 'device'} mode"
        })
    
    return jsonify({"status": "error", "message": "Invalid configuration"})