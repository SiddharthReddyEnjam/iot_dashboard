# app/config.py

# Data source configuration
USE_MOCK = True  # Set to False to use real serial device
SERIAL_PORT = 'COM7'  # Default COM port - can be changed via UI
BAUD_RATE = 9600  # Default baud rate - can be changed via UI
TIMEOUT = 1

# Available baud rates for the UI dropdown
AVAILABLE_BAUD_RATES = [9600, 19200, 38400, 57600, 115200]

# File settings
CSV_FILE = 'payload_log.csv'

# Mock data settings
MOCK_UPDATE_INTERVAL = 2  # seconds (increased to match UI)
MOCK_REALISTIC_VARIATIONS = True  # Enable realistic sensor variations

# Dashboard settings
MAX_CHART_POINTS = 50  # Maximum points to show on charts
UPDATE_FREQUENCY = 2000  # milliseconds for frontend updates

# GPS coordinate conversion settings
DEFAULT_GPS_FORMAT = "DDMM.MMMMM"  # Format from your device

# Temperature thresholds for color coding
TEMP_THRESHOLDS = {
    'cold': 15,    # Below 15°C
    'normal': 25,  # 15-25°C
    'warm': 35,    # 25-35°C
    'hot': 35      # Above 35°C
}

# Thermal system settings
THERMAL_TARGET_MIN = 29.4
THERMAL_TARGET_MAX = 29.6