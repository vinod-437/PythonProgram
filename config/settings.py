import os

def build_connection_string(server, database, username, password):
    if server and database and username and password:
        return f"Driver={{SQL Server}};Server={server};Database={database};UID={username};PWD={password};Timeout=45;"
    return None

def get_db_connection_string():
    # Prefer constructing from components
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    
    built_str = build_connection_string(server, database, username, password)
    if built_str:
        return built_str
        
    return os.getenv('DB_CONNECTION_STRING')

def get_db_server():
    return os.getenv('DB_SERVER')

def get_db_name():
    return os.getenv('DB_NAME')

def get_db_user():
    return os.getenv('DB_USER')

def get_db_password():
    return os.getenv('DB_PASSWORD')

def get_tp_api_url():
    return os.getenv('TP_API_URL')

def get_api_username():
    return os.getenv('API_USERNAME')

def get_api_password():
    return os.getenv('API_PASSWORD')

def get_log_path():
    return os.getenv('LOG_PATH', './Logs/')

def get_log_level():
    return os.getenv('LOG_LEVEL', 'INFO')

def get_log_to_file():
    val = os.getenv('LOG_TO_FILE', 'True')
    return val.lower() in ('true', '1', 'yes')
