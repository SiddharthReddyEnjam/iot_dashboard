from app import create_app, socketio
from app.serial_reader import start_reader
from app import config
import os
import time
import threading

def main():
    # Create Flask app
    app = create_app()
    
    # Print startup information
    print("=" * 70)
    print("🚀 IoT Real-Time Dashboard Starting...")
    print(f"📊 Data Mode: {'Mock Data' if config.USE_MOCK else 'Serial Device'}")
    if not config.USE_MOCK:
        print(f"📡 Serial Port: {config.SERIAL_PORT}")
        print(f"⚡ Baud Rate: {config.BAUD_RATE}")
    print(f"📁 CSV Log: {config.CSV_FILE}")
    print(f"🌐 Dashboard: http://localhost:5001")
    print(f"⏰ Update Interval: {config.MOCK_UPDATE_INTERVAL} seconds")
    print("=" * 70)
    
    # Create CSV file if it doesn't exist
    if not os.path.exists(config.CSV_FILE):
        with open(config.CSV_FILE, 'w') as f:
            f.write("timestamp,lat,lon,alt,satellites,utc_time,rtc_date,rtc_time,ms5611_temp,pressure,ds18b20_temp,scd30_temp,rh,co2,thermal_temp,heating_status,target_range\n")
        print(f"📄 Created CSV file: {config.CSV_FILE}")
    
    # Start data reader in a separate thread after a short delay
    def delayed_start_reader():
        time.sleep(2)  # Give Flask time to fully initialize
        print("🔧 Starting data reader...")
        try:
            start_reader(socketio)
            print("✅ Data reader started successfully")
        except Exception as e:
            print(f"❌ Error starting data reader: {e}")
            import traceback
            traceback.print_exc()
    
    reader_thread = threading.Thread(target=delayed_start_reader, daemon=True)
    reader_thread.start()
    
    # Run the application
    try:
        print("🌐 Starting web server...")
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
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()