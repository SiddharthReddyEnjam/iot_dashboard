# app/config.py

# Data source configuration
USE_MOCK = True  # Set to False to use real serial device
SERIAL_PORT = 'COM13'  # Adjust for your system (e.g., '/dev/ttyUSB0' on Linux/Mac)
BAUD_RATE = 9600
TIMEOUT = 1

# File settings
CSV_FILE = 'payload_log.csv'

# Mock data settings
MOCK_UPDATE_INTERVAL = 1  # seconds
MOCK_REALISTIC_VARIATIONS = True  # Enable realistic sensor variations

# Dashboard settings
MAX_CHART_POINTS = 50  # Maximum points to show on charts
UPDATE_FREQUENCY = 1000  # milliseconds for frontend updates