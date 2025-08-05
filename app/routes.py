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
        "available_baud_rates": config.AVAILABLE_BAUD_RATES,
        "max_chart_points": config.MAX_CHART_POINTS,
        "update_frequency": config.UPDATE_FREQUENCY,
        "timeout": config.TIMEOUT
    })

@main.route("/api/config", methods=['POST'])
def update_config():
    """Update configuration (COM port, baud rate, mock/real mode)"""
    data = request.get_json()
    response_messages = []
    
    # Handle data source toggle
    if 'use_mock' in data:
        old_mode = config.USE_MOCK
        config.USE_MOCK = data['use_mock']
        
        # Restart the data reader with new mode
        from .serial_reader import stop_reader, start_reader
        from . import socketio
        
        print(f"🔄 Switching from {'mock' if old_mode else 'device'} to {'mock' if config.USE_MOCK else 'device'} mode")
        
        stop_reader()
        start_reader(socketio)
        
        response_messages.append(f"Switched to {'mock' if config.USE_MOCK else 'device'} mode")
    
    # Handle COM port update
    if 'serial_port' in data:
        old_port = config.SERIAL_PORT
        new_port = data['serial_port'].strip().upper()
        
        # Validate COM port format
        if not new_port.startswith('COM') and not new_port.startswith('/dev/'):
            return jsonify({
                "status": "error", 
                "message": "Invalid COM port format. Use COMx for Windows or /dev/ttyUSBx for Linux/Mac"
            })
        
        config.SERIAL_PORT = new_port
        print(f"📡 COM port updated from {old_port} to {new_port}")
        
        # Restart reader if using device mode
        if not config.USE_MOCK:
            from .serial_reader import stop_reader, start_reader
            from . import socketio
            
            stop_reader()
            start_reader(socketio)
        
        response_messages.append(f"COM port updated to {new_port}")
    
    # Handle baud rate update
    if 'baud_rate' in data:
        old_baud = config.BAUD_RATE
        new_baud = int(data['baud_rate'])
        
        # Validate baud rate
        if new_baud not in config.AVAILABLE_BAUD_RATES:
            return jsonify({
                "status": "error",
                "message": f"Invalid baud rate. Available rates: {config.AVAILABLE_BAUD_RATES}"
            })
        
        config.BAUD_RATE = new_baud
        print(f"⚡ Baud rate updated from {old_baud} to {new_baud}")
        
        # Restart reader if using device mode
        if not config.USE_MOCK:
            from .serial_reader import stop_reader, start_reader
            from . import socketio
            
            stop_reader()
            start_reader(socketio)
        
        response_messages.append(f"Baud rate updated to {new_baud}")
    
    # Handle timeout update
    if 'timeout' in data:
        old_timeout = config.TIMEOUT
        new_timeout = float(data['timeout'])
        
        if new_timeout <= 0 or new_timeout > 10:
            return jsonify({
                "status": "error",
                "message": "Timeout must be between 0.1 and 10 seconds"
            })
        
        config.TIMEOUT = new_timeout
        print(f"⏱️ Timeout updated from {old_timeout} to {new_timeout}")
        response_messages.append(f"Timeout updated to {new_timeout}s")
    
    if response_messages:
        return jsonify({
            "status": "success", 
            "message": "; ".join(response_messages)
        })
    
    return jsonify({"status": "error", "message": "No valid configuration parameters provided"})

@main.route("/api/test-connection")
def test_connection():
    """Test the current serial connection"""
    if config.USE_MOCK:
        return jsonify({
            "status": "success",
            "message": "Currently using mock data",
            "connection": "mock"
        })
    
    try:
        import serial
        
        # Try to open the connection briefly
        test_conn = serial.Serial(
            config.SERIAL_PORT, 
            config.BAUD_RATE, 
            timeout=1
        )
        test_conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Successfully connected to {config.SERIAL_PORT} at {config.BAUD_RATE} baud",
            "connection": "device"
        })
        
    except serial.SerialException as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to {config.SERIAL_PORT}: {str(e)}",
            "connection": "failed"
        })
    except ImportError:
        return jsonify({
            "status": "error",
            "message": "pyserial not installed. Install with: pip install pyserial",
            "connection": "missing_library"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "connection": "error"
        })

@main.route("/api/available-ports")
def get_available_ports():
    """Get list of available COM ports"""
    try:
        import serial.tools.list_ports
        
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append({
                "device": port_info.device,
                "description": port_info.description,
                "hwid": port_info.hwid
            })
        
        return jsonify({
            "status": "success",
            "ports": ports
        })
        
    except ImportError:
        return jsonify({
            "status": "error",
            "message": "pyserial not installed",
            "ports": []
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error scanning ports: {str(e)}",
            "ports": []
        })