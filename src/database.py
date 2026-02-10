
import pyodbc
import os
import logging

logger = logging.getLogger("PaythonProgram")

def get_db_connection():
    conn_str = os.getenv('DB_CONNECTION_STRING')
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def get_bio_punches_data():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Equivalent to: cmd.Parameters.Add("@action", SqlDbType.VarChar, 500).Value = "getBioPunchesData";
        sql = "{CALL uspManageBioPunchesData (?)}"
        params = ('getBioPunchesData',)
        
        cursor.execute(sql, params)
        
        row = cursor.fetchone()
        if row:
            return row[0] # Assuming data is in the first column
        return None
        
    except Exception as e:
        logger.error(f"Error fetching bio punches data: {e}")
        raise
    finally:
        if conn:
            conn.close()

def update_sync_status(txn_ids):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Equivalent to: 
        # cmd.Parameters.Add("@action", SqlDbType.VarChar, 500).Value = "UpdateBioSyncData";
        # cmd.Parameters.Add("@txnIds", SqlDbType.VarChar,int.MaxValue).Value = transIds;
        
        sql = "{CALL uspManageBioPunchesData (?, ?)}"
        params = ('UpdateBioSyncData', txn_ids)
        
        cursor.execute(sql, params)
        conn.commit()
        
        return True
        return None

    except Exception as e:
        logger.error(f"Error updating sync status: {e}")
        raise
    finally:
        if conn:
            conn.close()
