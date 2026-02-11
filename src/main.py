
import os
import sys
from dotenv import load_dotenv

# Add the project root to the python path
if getattr(sys, 'frozen', False):
    # If frozen, the executable's directory should be in sys.path so 'config' package is found there
    application_path = os.path.dirname(sys.executable)
    sys.path.insert(0, application_path)
else:
    # If script, use standard project root logic
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
    from src.logger import setup_logger
    from src.database import get_bio_punches_data, update_sync_status
    from src.api_client import send_punch_data
except ImportError:
    # Fallback for frozen executable where src might be flattened or not a package
    # This assumes PyInstaller bundles contents of src at root or similar
    from config import settings
    from logger import setup_logger
    from database import get_bio_punches_data, update_sync_status
    from api_client import send_punch_data

def get_application_path():
    """
    Returns the path to the application directory.
    If running as a PyInstaller bundle, this is the directory of the executable.
    If running as a script, this is the directory of the script (project root).
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as python script
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_sync():
    """
    Runs the synchronization process and returns a result dictionary.
    Returns:
        dict: {'success': bool, 'message': str}
    """
    # Determine base path
    base_path = get_application_path()
    
    # Load configuration
    env_path = os.path.join(base_path, 'config', '.env')
    load_dotenv(env_path)
    
    # Setup logging
    logger = setup_logger()
    logger.info("Starting TanhkapayPythonProgram Data Sync...")

    try:
        # 1. Fetch data from DB
        logger.info("Fetching data from database...")
        data = get_bio_punches_data()
        
        if not data:
            logger.info("No record found for syncing.")
            return {'success': True, 'message': "No record found for syncing."}

        # 2. Sync with API
        logger.info("Syncing data with API...")
        api_result = send_punch_data(data)
        
        if api_result and api_result.get('success'):
             txn_ids = api_result.get('txn_ids')
             if txn_ids:
                 # 3. Update DB status
                 logger.info(f"Records Sync Successfully. Updating status for txn ids: {txn_ids}")
                 update_result = update_sync_status(txn_ids)
                 if update_result:
                     logger.info("Database updated successfully.")
                     return {'success': True, 'message': f"Successfully synced {len(txn_ids)} records."}
                 else:
                     logger.warning("Records synced but failed to update database status.")
                     return {'success': False, 'message': "Records synced but failed to update database status."}
             else:
                 logger.warning("API returned success but no transaction IDs.")
                 return {'success': True, 'message': "API returned success but no transaction IDs."}
        else:
             error_msg = f"API Sync failed. Message: {api_result.get('message') if api_result else 'Unknown error'}"
             logger.error(error_msg)
             return {'success': False, 'message': error_msg}

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return {'success': False, 'message': f"An unexpected error occurred: {e}"}

def main():
    result = run_sync()
    print(result['message'])

if __name__ == "__main__":
    main()
