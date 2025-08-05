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
    import serial.tools.list_ports
except ImportError:
    print("⚠️  pyserial not installed. Install with: pip install pyserial")
    serial = None

class DataReader:
    def __init__(self, socketio):
        self.socketio = socketio
        self.running = False
        self.serial_conn = None
        self.start_time = time.time()
        self.data_buffer = ""
        
        # Initialize CSV with headers if file doesn't exist
        try:
            with open(config.CSV_FILE, 'x', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'lat_decimal', 'lon_decimal', 'lat_raw', 'lon_raw', 
                    'alt', 'satellites', 'utc_time', 'rtc_date', 'rtc_time', 
                    'ms5611_temp', 'pressure', 'ds18b20_temp', 'scd30_temp', 
                    'rh', 'co2', 'thermal_temp', 'heating_status', 'target_range'
                ])
        except FileExistsError:
            pass
        
        print(f"✅ DataReader initialized with socketio: {socketio}")

    def format_date_windows_compatible(self, dt):
        """Format date in M/D/YYYY format (Windows compatible)"""
        # Use %m/%d/%Y and then strip leading zeros manually
        formatted = dt.strftime("%m/%d/%Y")
        # Remove leading zeros from month and day
        parts = formatted.split('/')
        month = str(int(parts[0]))  # Remove leading zero from month
        day = str(int(parts[1]))    # Remove leading zero from day  
        year = parts[2]
        return f"{month}/{day}/{year}"

    def generate_realistic_mock_data(self):
        """Generate realistic mock data matching your device format"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # Time-based variations for realistic sensor behavior
        time_factor = math.sin(elapsed / 60) * 0.5 + 0.5  # Slow sine wave
        daily_factor = math.sin(elapsed / 3600) * 0.3 + 0.7  # Daily variation
        
        # GPS coordinates in DDMM.MMMMM format (like your device)
        base_lat = 3325.271972
        base_lon = 11155.243164
        
        latest_data["lat"] = base_lat + (random.uniform(-0.01, 0.01) + math.sin(elapsed/30) * 0.005)
        latest_data["lon"] = base_lon + (random.uniform(-0.01, 0.01) + math.cos(elapsed/30) * 0.005)
        latest_data["alt"] = round(378.0 + math.sin(elapsed / 120) * 30 + random.uniform(-10, 10), 1)
        latest_data["satellites"] = random.randint(7, 12)
        
        # Time data - Windows compatible formatting
        now = datetime.now()
        latest_data["utc_time"] = now.strftime("%H:%M:%S")
        latest_data["rtc_date"] = self.format_date_windows_compatible(now)  # Windows compatible
        latest_data["rtc_time"] = now.strftime("%H:%M:%S")
        
        # Temperature sensors with realistic correlations
        base_temp = 25 + daily_factor * 5  # 20-30°C range
        temp_noise = random.uniform(-0.3, 0.3)
        
        latest_data["ms5611_temp"] = round(base_temp + temp_noise + random.uniform(-1, 1), 2)
        latest_data["ds18b20_temp"] = round(base_temp + temp_noise + random.uniform(-0.8, 0.8), 2)
        latest_data["scd30_temp"] = round(base_temp + temp_noise + random.uniform(-0.6, 0.6), 2)
        latest_data["thermal_temp"] = round(26.04 + math.sin(elapsed / 200) * 2 + random.uniform(-0.5, 0.5), 2)
        
        # Pressure with altitude correlation
        latest_data["pressure"] = round(970.81 - (latest_data["alt"] - 378) * 0.12 + random.uniform(-2, 2), 2)
        
        # Humidity with inverse temperature correlation
        base_humidity = 50 - (base_temp - 25) * 1.5
        latest_data["rh"] = round(max(20, min(80, base_humidity + random.uniform(-5, 5))), 2)
        
        # CO2 with realistic atmospheric variations
        co2_base = 700 + math.sin(elapsed / 600) * 150 + math.sin(elapsed / 60) * 20
        latest_data["co2"] = round(max(400, min(1200, co2_base + random.uniform(-30, 30))), 1)
        
        # Thermal system logic
        target_temp = (config.THERMAL_TARGET_MIN + config.THERMAL_TARGET_MAX) / 2
        latest_data["heating_status"] = "ON" if latest_data["thermal_temp"] < target_temp else "OFF"
        latest_data["target_range"] = f"{config.THERMAL_TARGET_MIN} - {config.THERMAL_TARGET_MAX}"
        
        print(f"📊 Generated mock data: GPS={latest_data['lat']:.2f},{latest_data['lon']:.2f}, Alt={latest_data['alt']}m, CO2={latest_data['co2']}ppm")

    def parse_telemetry_block(self, data_block):
        """Parse a complete telemetry data block"""
        try:
            lines = data_block.strip().split('\n')
            data_updated = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # GPS coordinates and altitude
                if line.startswith('GPS:'):
                    # GPS: 3325.271972, 11155.243164 (Alt: 378.0 m)
                    gps_pattern = r'GPS:\s*([\d.]+),\s*([\d.]+)\s*\(Alt:\s*([\d.]+)\s*m\)'
                    match = re.search(gps_pattern, line)
                    if match:
                        latest_data["lat"] = float(match.group(1))
                        latest_data["lon"] = float(match.group(2))
                        latest_data["alt"] = float(match.group(3))
                        data_updated = True
                
                # Satellites
                elif line.startswith('Sats:'):
                    match = re.search(r'Sats:\s*(\d+)', line)
                    if match:
                        latest_data["satellites"] = int(match.group(1))
                        data_updated = True
                
                # UTC Time
                elif line.startswith('UTC Time:'):
                    match = re.search(r'UTC Time:\s*([\d:]+)', line)
                    if match:
                        latest_data["utc_time"] = match.group(1)
                        data_updated = True
                
                # RTC Date
                elif line.startswith('RTC Date:'):
                    match = re.search(r'RTC Date:\s*([\d/]+)', line)
                    if match:
                        latest_data["rtc_date"] = match.group(1)
                        data_updated = True
                
                # RTC Time
                elif line.startswith('RTC Time:'):
                    match = re.search(r'RTC Time:\s*([\d:]+)', line)
                    if match:
                        latest_data["rtc_time"] = match.group(1)
                        data_updated = True
                
                # MS5611 Temperature
                elif line.startswith('MS5611 Temp:'):
                    match = re.search(r'MS5611 Temp:\s*([\d.-]+)', line)
                    if match:
                        latest_data["ms5611_temp"] = float(match.group(1))
                        data_updated = True
                
                # Pressure
                elif line.startswith('Pressure:'):
                    match = re.search(r'Pressure:\s*([\d.-]+)', line)
                    if match:
                        latest_data["pressure"] = float(match.group(1))
                        data_updated = True
                
                # DS18B20 Temperature
                elif line.startswith('DS18B20 Temp:'):
                    # DS18B20 Temp: 25.62 °C (78.12 °F)
                    match = re.search(r'DS18B20 Temp:\s*([\d.-]+)', line)
                    if match:
                        latest_data["ds18b20_temp"] = float(match.group(1))
                        data_updated = True
                
                # SCD30 Temperature
                elif line.startswith('SCD30 Temp:'):
                    match = re.search(r'SCD30 Temp:\s*([\d.-]+)', line)
                    if match:
                        latest_data["scd30_temp"] = float(match.group(1))
                        data_updated = True
                
                # Humidity
                elif line.startswith('Humidity:'):
                    match = re.search(r'Humidity:\s*([\d.-]+)', line)
                    if match:
                        latest_data["rh"] = float(match.group(1))
                        data_updated = True
                
                # CO2
                elif line.startswith('CO2:'):
                    match = re.search(r'CO2:\s*([\d.-]+)', line)
                    if match:
                        latest_data["co2"] = float(match.group(1))
                        data_updated = True
                
                # Thermal Temperature
                elif line.startswith('Thermal Temp:'):
                    # Thermal Temp: 26.04 °C (78.87 °F)
                    match = re.search(r'Thermal Temp:\s*([\d.-]+)', line)
                    if match:
                        latest_data["thermal_temp"] = float(match.group(1))
                        data_updated = True
                
                # Heating Status
                elif line.startswith('Heating Status:'):
                    match = re.search(r'Heating Status:\s*(\w+)', line)
                    if match:
                        latest_data["heating_status"] = match.group(1)
                        data_updated = True
                
                # Target Range
                elif line.startswith('Target Range:'):
                    match = re.search(r'Target Range:\s*([\d.]+ - [\d.]+)', line)
                    if match:
                        latest_data["target_range"] = match.group(1)
                        data_updated = True
            
            if data_updated:
                print(f"📡 Parsed telemetry: GPS=({latest_data.get('lat', 'N/A')}, {latest_data.get('lon', 'N/A')}), Alt={latest_data.get('alt', 'N/A')}m, CO2={latest_data.get('co2', 'N/A')}ppm")
            
            return data_updated
                    
        except Exception as e:
            print(f"❌ Error parsing telemetry data: {e}")
            return False

    def read_serial_data(self):
        """Read data from serial device with improved buffering"""
        try:
            if not self.serial_conn:
                if not serial:
                    print("❌ pyserial not available")
                    return False
                    
                print(f"📡 Attempting to connect to {config.SERIAL_PORT} at {config.BAUD_RATE} baud...")
                self.serial_conn = serial.Serial(
                    config.SERIAL_PORT, 
                    config.BAUD_RATE, 
                    timeout=config.TIMEOUT
                )
                time.sleep(2)  # Give device time to initialize
                print(f"✅ Connected to {config.SERIAL_PORT}")
            
            # Read data with buffering
            start_time = time.time()
            new_data = ""
            
            while time.time() - start_time < 5:  # Read for up to 5 seconds
                if self.serial_conn.in_waiting > 0:
                    try:
                        chunk = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                        new_data += chunk
                        self.data_buffer += chunk
                        
                        # Look for complete telemetry blocks
                        if "=== COMBINED TELEMETRY ===" in self.data_buffer and "Target Range:" in self.data_buffer:
                            # Extract the complete block
                            start_marker = "=== COMBINED TELEMETRY ==="
                            start_idx = self.data_buffer.find(start_marker)
                            
                            if start_idx != -1:
                                block_start = start_idx + len(start_marker)
                                # Look for the end of this block (next start marker or end of buffer)
                                next_start = self.data_buffer.find(start_marker, block_start)
                                
                                if next_start != -1:
                                    block = self.data_buffer[block_start:next_start]
                                    self.data_buffer = self.data_buffer[next_start:]  # Keep remaining data
                                else:
                                    block = self.data_buffer[block_start:]
                                    self.data_buffer = ""
                                
                                # Parse the complete block
                                if block.strip():
                                    return self.parse_telemetry_block(block)
                        
                        # Prevent buffer from getting too large
                        if len(self.data_buffer) > 2000:
                            self.data_buffer = self.data_buffer[-1000:]  # Keep last 1000 chars
                            
                    except UnicodeDecodeError:
                        print("⚠️ Unicode decode error, skipping chunk")
                        continue
                        
                else:
                    time.sleep(0.1)
            
            return False
            
        except serial.SerialException as e:
            print(f"❌ Serial error: {e}")
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None
            update_system_status("device", error=True)
            return False
        except Exception as e:
            print(f"❌ Unexpected error in serial reading: {e}")
            return False

    def convert_gps_to_decimal(self, coord):
        """Convert DDMM.MMMMM format to decimal degrees"""
        if coord == 0:
            return 0
        
        degrees = int(coord / 100)
        minutes = coord - (degrees * 100)
        return degrees + (minutes / 60)

    def log_data_to_csv(self, timestamp):
        """Log current data to CSV file with decimal GPS coordinates"""
        try:
            # Convert GPS to decimal
            lat_decimal = self.convert_gps_to_decimal(latest_data.get("lat", 0))
            lon_decimal = -self.convert_gps_to_decimal(latest_data.get("lon", 0))  # Assuming West longitude
            
            with open(config.CSV_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    lat_decimal,
                    lon_decimal,
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
            # Add decimal GPS coordinates for frontend
            lat_decimal = self.convert_gps_to_decimal(latest_data.get("lat", 0))
            lon_decimal = -self.convert_gps_to_decimal(latest_data.get("lon", 0))  # West longitude
            
            data_to_send = {
                **latest_data, 
                "lat_decimal": lat_decimal,
                "lon_decimal": lon_decimal,
                "timestamp": timestamp, 
                "source": "mock" if config.USE_MOCK else "device"
            }
            
            print(f"🚀 Emitting data: GPS=({lat_decimal:.4f}, {lon_decimal:.4f}), Alt={data_to_send.get('alt', 'N/A')}m, CO2={data_to_send.get('co2', 'N/A')}ppm")
            self.socketio.emit("new_data", data_to_send)
            print(f"✅ Data emitted successfully")
            
        except Exception as e:
            print(f"❌ Error emitting data: {e}")
            import traceback
            traceback.print_exc()

    def run_reader(self):
        """Main reader loop"""
        print(f"🚀 Starting data reader - Mode: {'Mock' if config.USE_MOCK else 'Serial Device'}")
        print(f"📡 Port: {config.SERIAL_PORT} | Baud: {config.BAUD_RATE} | Timeout: {config.TIMEOUT}s")
        print(f"⏰ Update interval: {config.MOCK_UPDATE_INTERVAL} seconds")
        
        iteration_count = 0
        consecutive_failures = 0
        max_failures = 5
        
        while self.running:
            try:
                timestamp = time.time()
                data_updated = False
                iteration_count += 1
                
                print(f"🔄 Reader iteration #{iteration_count} ({'Mock' if config.USE_MOCK else 'Device'})")
                
                if config.USE_MOCK:
                    self.generate_realistic_mock_data()
                    data_updated = True
                    consecutive_failures = 0
                else:
                    data_updated = self.read_serial_data()
                    
                    if data_updated:
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        print(f"⚠️ No data received (failure #{consecutive_failures}/{max_failures})")
                        
                        if consecutive_failures >= max_failures:
                            print(f"❌ Too many failures, switching to mock mode temporarily")
                            # Don't actually switch config.USE_MOCK, just generate mock data for this iteration
                            self.generate_realistic_mock_data()
                            data_updated = True
                            consecutive_failures = 0
                
                if data_updated:
                    print(f"📈 Data updated, logging and emitting...")
                    self.update_history(timestamp)
                    self.log_data_to_csv(timestamp)
                    self.emit_data(timestamp)
                    update_system_status("mock" if config.USE_MOCK else "device")
                else:
                    print(f"⚠️ No data update in iteration #{iteration_count}")
                
                time.sleep(config.MOCK_UPDATE_INTERVAL)
                
            except KeyboardInterrupt:
                print("🛑 Reader stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in reader loop: {e}")
                import traceback
                traceback.print_exc()
                consecutive_failures += 1
                time.sleep(1)  # Brief pause on error
                
                if consecutive_failures >= max_failures:
                    print("❌ Too many errors, stopping reader")
                    break

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
            try:
                self.serial_conn.close()
                print("📡 Serial connection closed")
            except:
                pass
            self.serial_conn = None

# Global reader instance
reader_instance = None

def start_reader(socketio):
    """Start the data reader"""
    global reader_instance
    print(f"🚀 start_reader called with socketio: {socketio}")
    
    if reader_instance is not None:
        print("⚠️ DataReader already exists, stopping previous instance")
        reader_instance.stop()
        time.sleep(1)  # Give it time to stop
    
    reader_instance = DataReader(socketio)
    thread = reader_instance.start()
    
    # Give it a moment to start
    time.sleep(0.5)
    
    return thread

def stop_reader():
    """Stop the data reader"""
    global reader_instance
    if reader_instance:
        reader_instance.stop()
        reader_instance = None

def get_available_ports():
    """Get list of available serial ports"""
    if not serial:
        return []
    
    try:
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append({
                "device": port_info.device,
                "description": port_info.description,
                "hwid": port_info.hwid
            })
        return ports
    except Exception as e:
        print(f"Error getting available ports: {e}")
        return []

def test_serial_connection(port=None, baud_rate=None):
    """Test serial connection with specified or default settings"""
    if not serial:
        return False, "pyserial not installed"
    
    test_port = port or config.SERIAL_PORT
    test_baud = baud_rate or config.BAUD_RATE
    
    try:
        test_conn = serial.Serial(test_port, test_baud, timeout=1)
        test_conn.close()
        return True, f"Successfully connected to {test_port} at {test_baud} baud"
    except serial.SerialException as e:
        return False, f"Failed to connect to {test_port}: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"