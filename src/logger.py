
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
    logger = logging.getLogger("TanhkapayPythonProgram")
    
    # Set level
    level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(level)

    # Check if file logging is enabled
    log_to_file = os.getenv('LOG_TO_FILE', 'True').lower() in ('true', '1', 'yes')

    # Add handlers (check if they exist to avoid duplicates)
    has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    has_stream_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers)
    
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    if log_to_file and not has_file_handler:
        log_filename = f"Log_{datetime.now().strftime('%Y-%m-%d')}.txt"
        file_handler = logging.FileHandler(os.path.join(log_path, log_filename))
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    
    # Note: If LOG_TO_FILE is False, we don't remove existing file handlers here, 
    # but normally this runs once or we assume the restart handles it.
    
    if not has_stream_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

    return logger
