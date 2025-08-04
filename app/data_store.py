from collections import defaultdict, deque
import time

# Latest sensor data with metadata - updated for new format
latest_data = {
    "lat": 3325.271972,        # GPS coordinates in DDMM.MMMMM format
    "lon": 11155.243164,
    "alt": 378.0,
    "satellites": 9,
    "utc_time": "22:42:36",
    "rtc_date": "8/2/2025",
    "rtc_time": "15:42:35",
    "ms5611_temp": 25.95,
    "pressure": 970.81,
    "ds18b20_temp": 25.62,
    "scd30_temp": 26.91,
    "rh": 39.73,
    "co2": 732.9,
    "thermal_temp": 26.04,
    "heating_status": "ON",
    "target_range": "29.4 - 29.6"
}

# History for plotting (limited size for performance)
history = defaultdict(lambda: deque(maxlen=100))

# System status
system_status = {
    "last_update": time.time(),
    "data_source": "mock",
    "connection_status": "connected",
    "error_count": 0,
    "uptime_start": time.time()
}

def get_system_uptime():
    """Get system uptime in seconds"""
    return time.time() - system_status["uptime_start"]

def update_system_status(source="mock", error=False):
    """Update system status"""
    system_status["last_update"] = time.time()
    system_status["data_source"] = source
    if error:
        system_status["error_count"] += 1
        system_status["connection_status"] = "error"
    else:
        system_status["connection_status"] = "connected"

def convert_gps_to_decimal(coord):
    """Convert DDMM.MMMMM format to decimal degrees"""
    if coord == 0:
        return 0
    
    degrees = int(coord / 100)
    minutes = coord - (degrees * 100)
    return degrees + (minutes / 60)

def get_decimal_coordinates():
    """Get GPS coordinates in decimal format for display"""
    lat_decimal = convert_gps_to_decimal(latest_data["lat"])
    lon_decimal = convert_gps_to_decimal(latest_data["lon"])
    # Assuming longitude is West (negative)
    if latest_data["lon"] > 10000:  # Likely a longitude > 100 degrees
        lon_decimal = -lon_decimal
    return lat_decimal, lon_decimal