
import requests
import json
import os
import logging
import base64

from config import settings

logger = logging.getLogger("PaythonProgram")

def send_punch_data(data):
    api_url = settings.get_tp_api_url()
    username = settings.get_api_username()
    password = settings.get_api_password()
    
    if not all([api_url, username, password]):
        logger.error("API configuration missing/incomplete.")
        return {'success': False, 'message': 'Configuration incomplete'}

    try:
        # Construct payload
        # The C# code does: var finalObj = "{\"punchingDetails\": " + result + "}";
        # We assume 'data' is already a JSON string from the DB, or we need to be careful.
        # If 'data' is a JSON string, we should parse it to ensure validity or just embed it.
        # Let's try to parse it to see if it's valid JSON, if not, treat as string?
        # The C# code treats it as a string concatenation, implying 'result' is a valid JSON fragment (e.g., an array or object).
        
        # We'll stick to string manipulation to match C# logic exactly for now, 
        # ensuring we don't double-escape if the DB returns a JSON string.
        payload_str = '{"punchingDetails": ' + str(data) + '}'
        
        # Check if valid JSON
        try:
            json.loads(payload_str)
        except json.JSONDecodeError:
            logger.warning("Constructed payload is not valid JSON. Proceeding anyway but API might fail.")

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Basic Auth
        # requests.auth.HTTPBasicAuth could be used, but let's match C# manual header construction to be safe?
        # C#: Convert.ToBase64String(Encoding.UTF8.GetBytes($"{username}:{password}"))
        # requests does this automatically with auth=(username, password)
        
        logger.info(f"Sending data to {api_url}")
        response = requests.post(
            api_url, 
            data=payload_str, 
            headers=headers, 
            auth=(username, password),
            timeout=300 # ServicePointManager set connection limit, but not timeout explicitly in C# snippet? default is usually high.
        )
        
        logger.info(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                # C# logic:
                # if (objJsonResult["message"].ToString().Substring(0, 24) == "Data Saved Successfully." && objJsonResult["commonData"].ToString() != "")
                
                message = response_json.get('message', '')
                common_data = response_json.get('commonData')
                
                if message.startswith("Data Saved Successfully.") and common_data:
                    # Parse commonData if it's a string (it seems to be JSON string inside JSON)
                    if isinstance(common_data, str):
                        common_data_json = json.loads(common_data)
                    else:
                        common_data_json = common_data
                        
                    txn_ids = common_data_json.get('successfullySavedTransactionIds')
                    
                    return {'success': True, 'txn_ids': txn_ids, 'message': message}
                else:
                    return {'success': False, 'message': message}
                    
            except Exception as e:
                logger.error(f"Failed to parse API response: {e}")
                return {'success': False, 'message': 'Invalid API Response'}
        else:
            return {'success': False, 'message': f"Http Error: {response.status_code}"}

    except Exception as e:
        logger.error(f"API Request failed: {e}")
        return {'success': False, 'message': str(e)}
