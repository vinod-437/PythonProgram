
import os

DB_CONNECTION_STRING = os.getenv('DB_CONNECTION_STRING')
TP_API_URL = os.getenv('TP_API_URL')
API_USERNAME = os.getenv('API_USERNAME')
API_PASSWORD = os.getenv('API_PASSWORD')
LOG_PATH = os.getenv('LOG_PATH', './Logs/')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
