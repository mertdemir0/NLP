"""
Docker configuration helper for NLP application.
Import this at the top of main.py to enable Docker compatibility.
"""
import os
import logging
import signal
import sys

# Create necessary directories
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Configure signal handlers for Docker graceful shutdown
def setup_signal_handlers():
    def signal_handler(sig, frame):
        logging.info("Received termination signal. Shutting down gracefully...")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# Get database path from environment
def get_db_path():
    return os.path.join(os.environ.get('DATA_DIR', 'data'), 'nuclear_news.db')

# Get environment variable with fallback
def get_env(var_name, default):
    return os.environ.get(var_name, default)

# Get environment variable as int with fallback
def get_env_int(var_name, default):
    return int(os.environ.get(var_name, default))

# Get environment variable as float with fallback
def get_env_float(var_name, default):
    return float(os.environ.get(var_name, default))
