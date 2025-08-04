from app import create_app, socketio
from app.serial_reader import start_reader
from app import config
import os

def main():
    # Create Flask app
    app = create_app()
    
    # Start data reader
    start_reader(socketio)
    
    # Print startup information
    print("=" * 60)
    print("🚀 IoT Real-Time Dashboard Starting...")
    print(f"📊 Data Mode: {'Mock Data' if config.USE_MOCK else 'Serial Device'}")
    if not config.USE_MOCK:
        print(f"📡 Serial Port: {config.SERIAL_PORT}")
        print(f"⚡ Baud Rate: {config.BAUD_RATE}")
    print(f"📁 CSV Log: {config.CSV_FILE}")
    print(f"🌐 Dashboard: http://localhost:5001")
    print("=" * 60)
    
    # Create CSV file if it doesn't exist
    if not os.path.exists(config.CSV_FILE):
        with open(config.CSV_FILE, 'w') as f:
            f.write("timestamp,lat,lon,alt,ms5611_temp,ds18b20_temp,scd30_temp,rh,co2\n")
        print(f"📄 Created CSV file: {config.CSV_FILE}")
    
    # Run the application
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    main()