import threading
import random
import time
import csv
import json
import math
import re
from datetime import datetime
from .data_store import latest_data, history, update_system_status
from . import config

try:
    import serial
except ImportError:
    print("⚠️  pyserial not installed. Install with: pip install pyserial")
    serial = None

class DataReader:
    def __init__(self, socketio):
        self.socketio = socketio
        self.running = False
        self.serial_conn = None
        self.start_time = time.time()
        
        # Initialize CSV with headers if file doesn't exist
        try:
            with open(config.CSV_FILE, 'x', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'lat', 'lon', 'alt', 'satellites', 'utc_time', 
                               'rtc_date', 'rtc_time', 'ms5611_temp', 'pressure', 'ds18b20_temp', 
                               'scd30_temp', 'rh', 'co2', 'thermal_temp', 'heating_status', 'target_range'])
        except FileExistsError:
            pass
        
        print(f"✅ DataReader initialized with socketio: {socketio}")

    def generate_realistic_mock_data(self):
        """Generate realistic mock data with time-based variations"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # Time-based variations for realistic sensor behavior
        time_factor = math.sin(elapsed / 60) * 0.5 + 0.5  # Slow sine wave over 1 minute
        daily_factor = math.sin(elapsed / 3600) * 0.3 + 0.7  # Daily temperature variation
        
        # GPS coordinates with slight drift (simulating movement)
        # Convert to DDMM.MMMMM format like your device
        base_lat_dd = 33.42119953  # 3325.271972 converted
        base_lon_dd = -111.92072733  # 11155.243164 converted (assuming West)
        
        # Convert back to DDMM.MMMMM format for display
        lat_dd = base_lat_dd + (random.uniform(-0.001, 0.001) + math.sin(elapsed/30) * 0.0005)
        lon_dd = abs(base_lon_dd) + (random.uniform(-0.001, 0.001) + math.cos(elapsed/30) * 0.0005)
        
        # Convert to DDMM.MMMMM format
        lat_deg = int(lat_dd)
        lat_min = (lat_dd - lat_deg) * 60
        latest_data["lat"] = round(lat_deg * 100 + lat_min, 6)
        
        lon_deg = int(lon_dd)
        lon_min = (lon_dd - lon_deg) * 60
        latest_data["lon"] = round(lon_deg * 100 + lon_min, 6)
        
        # Other mock data
        latest_data["alt"] = round(378 + math.sin(elapsed / 120) * 20 + random.uniform(-5, 5), 1)
        latest_data["satellites"] = random.randint(7, 12)
        
        # Time data
        now = datetime.now()
        latest_data["utc_time"] = now.strftime("%H:%M:%S")
        latest_data["rtc_date"] = now.strftime("%-m/%-d/%Y")
        latest_data["rtc_time"] = now.strftime("%H:%M:%S")
        
        # Temperature sensors with realistic correlations
        base_temp = 25 + daily_factor * 3  # 22-28°C range
        temp_noise = random.uniform(-0.5, 0.5)
        
        latest_data["ms5611_temp"] = round(base_temp + temp_noise + random.uniform(-1, 1), 2)
        latest_data["ds18b20_temp"] = round(base_temp + temp_noise + random.uniform(-0.8, 0.8), 2)
        latest_data["scd30_temp"] = round(base_temp + temp_noise + random.uniform(-0.6, 0.6), 2)
        latest_data["thermal_temp"] = round(base_temp + temp_noise + random.uniform(-0.4, 0.4), 2)
        
        # Pressure
        latest_data["pressure"] = round(970 + math.sin(elapsed / 300) * 5 + random.uniform(-2, 2), 2)
        
        # Humidity with inverse correlation to temperature
        base_humidity = 50 - (base_temp - 25) * 2
        latest_data["rh"] = round(max(20, min(80, base_humidity + random.uniform(-5, 5))), 2)
        
        # CO2 with realistic variations
        co2_base = 700 + math.sin(elapsed / 600) * 100  # Slow variation
        latest_data["co2"] = round(max(400, co2_base + random.uniform(-50, 50)), 1)
        
        # Thermal system
        latest_data["heating_status"] = "ON" if latest_data["thermal_temp"] < 29.5 else "OFF"
        latest_data["target_range"] = "29.4 - 29.6"
        
        print(f"📊 Generated mock data: CO2={latest_data['co2']}, Temp={latest_data['ms5611_temp']}°C")

    def parse_serial_data(self, data_block):
        """Parse the complete telemetry data block"""
        try:
            lines = data_block.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # GPS data
                if line.startswith('GPS:'):
                    # GPS: 3325.271972, 11155.243164 (Alt: 378.0 m)
                    gps_match = re.search(r'GPS:\s*([\d.]+),\s*([\d.]+)\s*\(Alt:\s*([\d.]+)\s*m\)', line)
                    if gps_match:
                        latest_data["lat"] = float(gps_match.group(1))
                        latest_data["lon"] = float(gps_match.group(2))
                        latest_data["alt"] = float(gps_match.group(3))
                
                # Satellites
                elif line.startswith('Sats:'):
                    sat_match = re.search(r'Sats:\s*(\d+)', line)
                    if sat_match:
                        latest_data["satellites"] = int(sat_match.group(1))
                
                # UTC Time
                elif line.startswith('UTC Time:'):
                    time_match = re.search(r'UTC Time:\s*([\d:]+)', line)
                    if time_match:
                        latest_data["utc_time"] = time_match.group(1)
                
                # RTC Date
                elif line.startswith('RTC Date:'):
                    date_match = re.search(r'RTC Date:\s*([\d/]+)', line)
                    if date_match:
                        latest_data["rtc_date"] = date_match.group(1)
                
                # RTC Time
                elif line.startswith('RTC Time:'):
                    time_match = re.search(r'RTC Time:\s*([\d:]+)', line)
                    if time_match:
                        latest_data["rtc_time"] = time_match.group(1)
                
                # MS5611 Temperature
                elif line.startswith('MS5611 Temp:'):
                    temp_match = re.search(r'MS5611 Temp:\s*([\d.]+)', line)
                    if temp_match:
                        latest_data["ms5611_temp"] = float(temp_match.group(1))
                
                # Pressure
                elif line.startswith('Pressure:'):
                    pressure_match = re.search(r'Pressure:\s*([\d.]+)', line)
                    if pressure_match:
                        latest_data["pressure"] = float(pressure_match.group(1))
                
                # DS18B20 Temperature
                elif line.startswith('DS18B20 Temp:'):
                    temp_match = re.search(r'DS18B20 Temp:\s*([\d.]+)', line)
                    if temp_match:
                        latest_data["ds18b20_temp"] = float(temp_match.group(1))
                
                # SCD30 Temperature
                elif line.startswith('SCD30 Temp:'):
                    temp_match = re.search(r'SCD30 Temp:\s*([\d.]+)', line)
                    if temp_match:
                        latest_data["scd30_temp"] = float(temp_match.group(1))
                
                # Humidity
                elif line.startswith('Humidity:'):
                    humidity_match = re.search(r'Humidity:\s*([\d.]+)', line)
                    if humidity_match:
                        latest_data["rh"] = float(humidity_match.group(1))
                
                # CO2
                elif line.startswith('CO2:'):
                    co2_match = re.search(r'CO2:\s*([\d.]+)', line)
                    if co2_match:
                        latest_data["co2"] = float(co2_match.group(1))
                
                # Thermal Temperature
                elif line.startswith('Thermal Temp:'):
                    temp_match = re.search(r'Thermal Temp:\s*([\d.]+)', line)
                    if temp_match:
                        latest_data["thermal_temp"] = float(temp_match.group(1))
                
                # Heating Status
                elif line.startswith('Heating Status:'):
                    status_match = re.search(r'Heating Status:\s*(\w+)', line)
                    if status_match:
                        latest_data["heating_status"] = status_match.group(1)
                
                # Target Range
                elif line.startswith('Target Range:'):
                    range_match = re.search(r'Target Range:\s*([\d.]+ - [\d.]+)', line)
                    if range_match:
                        latest_data["target_range"] = range_match.group(1)
            
            print(f"📡 Parsed serial data: GPS={latest_data.get('lat', 'N/A')}, CO2={latest_data.get('co2', 'N/A')}")
            return True
                    
        except Exception as e:
            print(f"❌ Error parsing serial data: {e}")
            return False

    def read_serial_data(self):
        """Read data from serial device"""
        try:
            if not self.serial_conn:
                if not serial:
                    print("❌ pyserial not available")
                    return False
                    
                self.serial_conn = serial.Serial(
                    config.SERIAL_PORT, 
                    config.BAUD_RATE, 
                    timeout=config.TIMEOUT
                )
                print(f"📡 Connected to {config.SERIAL_PORT}")
            
            # Read multiple lines to get complete data block
            data_block = ""
            start_time = time.time()
            
            while time.time() - start_time < 2:  # Read for up to 2 seconds
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        data_block += line + '\n'
                        # Check if we have a complete block
                        if 'Target Range:' in line:  # End of block marker
                            break
                else:
                    time.sleep(0.1)
            
            if data_block:
                return self.parse_serial_data(data_block)
            return False
            
        except serial.SerialException as e:
            print(f"❌ Serial error: {e}")
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
            update_system_status("device", error=True)
            return False
        except Exception as e:
            print(f"❌ Unexpected error in serial reading: {e}")
            return False

    def log_data_to_csv(self, timestamp):
        """Log current data to CSV file"""
        try:
            with open(config.CSV_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    latest_data.get("lat", ""),
                    latest_data.get("lon", ""),
                    latest_data.get("alt", ""),
                    latest_data.get("satellites", ""),
                    latest_data.get("utc_time", ""),
                    latest_data.get("rtc_date", ""),
                    latest_data.get("rtc_time", ""),
                    latest_data.get("ms5611_temp", ""),
                    latest_data.get("pressure", ""),
                    latest_data.get("ds18b20_temp", ""),
                    latest_data.get("scd30_temp", ""),
                    latest_data.get("rh", ""),
                    latest_data.get("co2", ""),
                    latest_data.get("thermal_temp", ""),
                    latest_data.get("heating_status", ""),
                    latest_data.get("target_range", "")
                ])
        except Exception as e:
            print(f"❌ CSV logging error: {e}")

    def update_history(self, timestamp):
        """Update history deques for charting"""
        history["time"].append(timestamp)
        for key, value in latest_data.items():
            if isinstance(value, (int, float)):  # Only numeric values for charts
                history[key].append(value)

    def emit_data(self, timestamp):
        """Emit data via WebSocket"""
        try:
            data_to_send = {
                **latest_data, 
                "timestamp": timestamp, 
                "source": "mock" if config.USE_MOCK else "device"
            }
            
            print(f"🚀 Emitting data via WebSocket: CO2={data_to_send.get('co2', 'N/A')}")
            self.socketio.emit("new_data", data_to_send)
            print(f"✅ Data emitted successfully")
            
        except Exception as e:
            print(f"❌ Error emitting data: {e}")
            import traceback
            traceback.print_exc()

    def run_reader(self):
        """Main reader loop"""
        print(f"🚀 Starting data reader - Mode: {'Mock' if config.USE_MOCK else 'Serial Device'}")
        print(f"⏰ Update interval: {config.MOCK_UPDATE_INTERVAL} seconds")
        
        iteration_count = 0
        
        while self.running:
            try:
                timestamp = time.time()
                data_updated = False
                iteration_count += 1
                
                print(f"🔄 Reader iteration #{iteration_count}")
                
                if config.USE_MOCK:
                    self.generate_realistic_mock_data()
                    data_updated = True
                else:
                    data_updated = self.read_serial_data()
                
                if data_updated:
                    print(f"📈 Data updated, logging and emitting...")
                    self.update_history(timestamp)
                    self.log_data_to_csv(timestamp)
                    self.emit_data(timestamp)
                    update_system_status("mock" if config.USE_MOCK else "device")
                else:
                    print(f"⚠️  No data update in iteration #{iteration_count}")
                
                time.sleep(config.MOCK_UPDATE_INTERVAL)
                
            except Exception as e:
                print(f"❌ Error in reader loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)  # Brief pause on error

    def start(self):
        """Start the reader thread"""
        print(f"🔧 Starting DataReader thread...")
        self.running = True
        thread = threading.Thread(target=self.run_reader, daemon=True, name="DataReader")
        thread.start()
        print(f"✅ DataReader thread started: {thread.name}")
        return thread

    def stop(self):
        """Stop the reader"""
        print(f"🛑 Stopping DataReader...")
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()
            print("📡 Serial connection closed")

# Global reader instance
reader_instance = None

def start_reader(socketio):
    """Start the data reader"""
    global reader_instance
    print(f"🚀 start_reader called with socketio: {socketio}")
    
    if reader_instance is not None:
        print("⚠️  DataReader already exists, stopping previous instance")
        reader_instance.stop()
    
    reader_instance = DataReader(socketio)
    thread = reader_instance.start()
    
    # Give it a moment to start, then test
    time.sleep(0.5)
    
    return thread

def stop_reader():
    """Stop the data reader"""
    global reader_instance
    if reader_instance:
        reader_instance.stop()
        reader_instance = None