
# TanhkapayPythonProgram - Biometric Data Sync

This is a Python-based application migrated from the original `.NET` `DotNetPropgram`. 
It fetches biometric punch data from a local SQL Server database and syncs it to a remote API.

## Prerequisites
- Python 3.x installed and added to PATH.
- SQL Server (LocalDB or Standard) with `uspManageBioPunchesData` stored procedure.
- Internet connection for API sync.

## Project Structure
```
TanhkapayPythonProgram/
├── config/
│   ├── .env          # Configuration file (Credentials, DB connection)
│   └── settings.py   # Config loader
├── src/
│   ├── main.py       # Entry point
│   ├── database.py   # Database interaction
│   ├── api_client.py # API client
│   └── logger.py     # Logging setup
├── Logs/             # Log files directory
├── requirements.txt  # Python dependencies
├── setup.bat         # Setup script (One-time)
└── run.bat           # Run script
```

## Setup
1.  Navigate to the `TanhkapayPythonProgram` directory.
2.  Double-click `setup.bat` to create a virtual environment and install dependencies.
    - Alternatively, run:
      ```bash
      python -m venv venv
      venv\Scripts\activate
      pip install -r requirements.txt
      ```

## Configuration
Edit `config/.env` to match your environment:
- **DB_CONNECTION_STRING**: Update `Server`, `User ID`, and `Password` if changed.
- **TP_API_URL**: API Endpoint.
- **API_USERNAME** / **API_PASSWORD**: API Credentials.

## Running the Application
Double-click `run.bat` to execute the sync process.
- Logs will be generated in the `Logs/` folder.

## Building Executable (Optional)
To create a standalone `.exe` file that doesn't require Python to be installed on the target machine:

1.  Double-click `build_exe.bat`.
    - This will install necessary build tools (like `PyInstaller`) if missing.
    - It will create a `dist` folder containing the executable and configuration.

2.  **Installation**:
    - Run `install_script.bat` to copy the application to `C:\TpayBiometricProgram` and create a desktop shortcut.

3.  **Configuration**:
    - The `config/.env` file is copied alongside the executable in `dist/config/`.
    - You can edit this file to change database connections or API credentials without rebuilding the application.

## Scheduling (Optional)
To run this automatically (e.g., every 15 minutes):
1.  Open **Windows Task Scheduler**.
2.  Create a new Basic Task.
3.  Action: **Start a Program**.
4.  Program/script: Browse to `run.bat` (or the built `TanhkapayPythonProgram.exe`).
5.  Set the trigger (e.g., Daily, repeat every 15 mins).

### Linux (Systemd)
1.  Copy `paython-sync.service` to `/etc/systemd/system/`.
2.  Edit the file to set correct paths.
3.  Enable and start:
    ```bash
    sudo systemctl enable paython-sync
    sudo systemctl start paython-sync
    ```

### Linux (Cron)
Run `crontab -e` and add:
```bash
*/15 * * * * /path/to/venv/bin/python /path/to/PaythonProgram/src/main.py >> /var/log/paython-sync.log 2>&1
```
