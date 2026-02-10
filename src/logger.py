
import logging
import os
import sys
from datetime import datetime

def setup_logger():
    # Load settings (assuming env vars are loaded)
    log_path = os.getenv('LOG_PATH', './Logs/')
    log_level_str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Ensure log directory exists
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    
    # Create a custom logger
    logger = logging.getLogger("PaythonProgram")
    
    # Set level
    level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(level)

    # Avoid adding handlers multiple times if setup_logger is called repeatedly
    if logger.handlers:
        return logger

    # Create handlers
    log_filename = f"Log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    file_handler = logging.FileHandler(os.path.join(log_path, log_filename))
    console_handler = logging.StreamHandler(sys.stdout)

    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(log_format)
    console_handler.setFormatter(log_format)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
