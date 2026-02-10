
import os
import sys
from dotenv import load_dotenv

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from src.logger import setup_logger
from src.database import get_bio_punches_data, update_sync_status
from src.api_client import send_punch_data

def main():
    # Load configuration
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))
    
    # Setup logging
    logger = setup_logger()
    logger.info("Starting PaythonProgram Data Sync...")

    try:
        # 1. Fetch data from DB
        logger.info("Fetching data from database...")
        data = get_bio_punches_data()
        
        if not data:
            logger.info("No record found for syncing.")
            return

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
                 else:
                     logger.warning("Records synced but failed to update database status.")
             else:
                 logger.warning("API returned success but no transaction IDs.")
        else:
             logger.error(f"API Sync failed. Message: {api_result.get('message') if api_result else 'Unknown error'}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        print(f"Unable to Sync Records {e}")

if __name__ == "__main__":
    main()
