from app import create_app, socketio
from app.serial_reader import start_reader, get_available_ports, test_serial_connection
from app import config
import os
import time
import threading
import sys

def print_banner():
    """Print startup banner"""
    print("=" * 80)
    print("🚀 IoT REAL-TIME DASHBOARD - HIGH ALTITUDE WEATHER BALLOON")
    print("=" * 80)
    print(f"📊 Data Mode: {'🎭 Mock Data' if config.USE_MOCK else '📡 Serial Device'}")
    
    if not config.USE_MOCK:
        print(f"📡 Serial Port: {config.SERIAL_PORT}")
        print(f"⚡ Baud Rate: {config.BAUD_RATE}")
        print(f"⏱️  Timeout: {config.TIMEOUT}s")
        
        # Test connection
        success, message = test_serial_connection()
        if success:
            print(f"✅ Serial Test: {message}")
        else:
            print(f"❌ Serial Test: {message}")
            print("⚠️  Will fall back to mock data if connection fails")
    
    print(f"📁 CSV Log: {config.CSV_FILE}")
    print(f"🌐 Dashboard: http://localhost:5001")
    print(f"⏰ Update Interval: {config.MOCK_UPDATE_INTERVAL} seconds")
    print(f"📈 Max Chart Points: {config.MAX_CHART_POINTS}")
    print("=" * 80)

def list_available_ports():
    """List available serial ports"""
    print("\n📡 AVAILABLE SERIAL PORTS:")
    print("-" * 40)
    
    ports = get_available_ports()
    if ports:
        for i, port in enumerate(ports, 1):
            print(f"{i}. {port['device']}")
            print(f"   Description: {port['description']}")
            print(f"   Hardware ID: {port['hwid']}")
            print()
    else:
        print("No serial ports found or pyserial not installed")
    print("-" * 40)

def setup_csv_file():
    """Create CSV file if it doesn't exist"""
    if not os.path.exists(config.CSV_FILE):
        with open(config.CSV_FILE, 'w', newline='') as f:
            import csv
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'lat_decimal', 'lon_decimal', 'lat_raw', 'lon_raw', 
                'alt', 'satellites', 'utc_time', 'rtc_date', 'rtc_time', 
                'ms5611_temp', 'pressure', 'ds18b20_temp', 'scd30_temp', 
                'rh', 'co2', 'thermal_temp', 'heating_status', 'target_range'
            ])
        print(f"📄 Created CSV file: {config.CSV_FILE}")
    else:
        print(f"📄 Using existing CSV file: {config.CSV_FILE}")

def delayed_start_reader():
    """Start data reader after Flask initialization"""
    time.sleep(2)  # Give Flask time to fully initialize
    print("\n🔧 Starting data reader...")
    
    try:
        start_reader(socketio)
        print("✅ Data reader started successfully")
        
        # Print some status info
        if config.USE_MOCK:
            print("🎭 Generating mock telemetry data")
        else:
            print(f"📡 Reading from {config.SERIAL_PORT} at {config.BAUD_RATE} baud")
            
    except Exception as e:
        print(f"❌ Error starting data reader: {e}")
        import traceback
        traceback.print_exc()
        print("⚠️  Dashboard will run without live data")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n🔍 CHECKING DEPENDENCIES:")
    print("-" * 30)
    
    # Check pyserial
    try:
        import serial
        print("✅ pyserial: Available")
    except ImportError:
        print("❌ pyserial: Not installed")
        print("   Install with: pip install pyserial")
    
    # Check Flask
    try:
        import flask
        print(f"✅ Flask: {flask.__version__}")
    except ImportError:
        print("❌ Flask: Not installed")
        return False
    
    # Check Flask-SocketIO
    try:
        import flask_socketio
        # print(f"✅ Flask-SocketIO: {flask_socketio.__version__}")
    except ImportError:
        print("❌ Flask-SocketIO: Not installed")
        return False
    
    print("-" * 30)
    return True

def interactive_config():
    """Interactive configuration setup"""
    if len(sys.argv) > 1 and sys.argv[1] == '--config':
        print("\n⚙️  INTERACTIVE CONFIGURATION")
        print("=" * 40)
        
        # Data source
        use_mock = input(f"Use mock data? (Y/n) [current: {'Y' if config.USE_MOCK else 'N'}]: ").strip().lower()
        if use_mock in ['n', 'no']:
            config.USE_MOCK = False
            
            # Serial port configuration
            list_available_ports()
            new_port = input(f"Enter COM port [{config.SERIAL_PORT}]: ").strip()
            if new_port:
                config.SERIAL_PORT = new_port
            
            # Baud rate
            print(f"Available baud rates: {config.AVAILABLE_BAUD_RATES}")
            new_baud = input(f"Enter baud rate [{config.BAUD_RATE}]: ").strip()
            if new_baud and new_baud.isdigit():
                baud_rate = int(new_baud)
                if baud_rate in config.AVAILABLE_BAUD_RATES:
                    config.BAUD_RATE = baud_rate
                else:
                    print(f"⚠️  Invalid baud rate, using {config.BAUD_RATE}")
        
        # Update interval
        new_interval = input(f"Update interval in seconds [{config.MOCK_UPDATE_INTERVAL}]: ").strip()
        if new_interval:
            try:
                config.MOCK_UPDATE_INTERVAL = float(new_interval)
            except ValueError:
                print(f"⚠️  Invalid interval, using {config.MOCK_UPDATE_INTERVAL}")
        
        print("=" * 40)
        print("✅ Configuration updated!")

def main():
    """Main application entry point"""
    print_banner()
    
    # Check dependencies first
    if not check_dependencies():
        print("❌ Missing required dependencies. Please install them and try again.")
        return
    
    # Interactive configuration if requested
    interactive_config()
    
    # List available ports if not using mock data
    if not config.USE_MOCK:
        list_available_ports()
    
    # Setup CSV file
    setup_csv_file()
    
    # Create Flask app
    print("\n🔧 Creating Flask application...")
    app = create_app()
    
    # Start data reader in background
    reader_thread = threading.Thread(target=delayed_start_reader, daemon=True)
    reader_thread.start()
    
    # Print final startup info
    print("\n🌐 DASHBOARD READY!")
    print(f"   Open your browser to: http://localhost:5001")
    print(f"   Press Ctrl+C to stop")
    print("\n📊 REAL-TIME DATA:")
    print(f"   Source: {'Mock Generator' if config.USE_MOCK else config.SERIAL_PORT}")
    print(f"   Update Rate: Every {config.MOCK_UPDATE_INTERVAL} seconds")
    print(f"   CSV Logging: {config.CSV_FILE}")
    print("\n" + "=" * 80)
    
    # Run the application
    try:
        socketio.run(
            app, 
            debug=False, 
            host='0.0.0.0', 
            port=5001, 
            allow_unsafe_werkzeug=True,
            use_reloader=False  # Disable reloader to prevent duplicate threads
        )
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
        print("📁 Data has been saved to:", config.CSV_FILE)
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()