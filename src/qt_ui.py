
import sys
import os
import threading
import schedule
import time
import logging
from datetime import datetime

# Adjust path to find src/config modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTabWidget, 
                             QLineEdit, QFormLayout, QTextEdit, QMessageBox, 
                             QSpinBox, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot, QTimer
# Import QIcon and QPixmap
from PyQt6.QtGui import QIcon, QPixmap

from src.main import run_sync
from config import settings
from dotenv import load_dotenv

# Ensure env is loaded
if getattr(sys, 'frozen', False):
    # If frozen, use executable directory
    base_path = os.path.dirname(sys.executable)
else:
    # If script, use parent of script directory
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env_path = os.path.join(base_path, 'config', '.env')
load_dotenv(env_path, override=True)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

# --- Workers ---

class SyncWorker(QObject):
    finished = pyqtSignal(dict)

    @pyqtSlot()
    def run(self):
        try:
            result = run_sync()
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({'success': False, 'message': str(e)})

class SchedulerThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        self.running = False
        self.wait()

# --- Logging ---

class QtLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)

# --- Main UI ---

class MainWindow(QMainWindow):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TankhaPay Biometric Records Synchronization")
        self.resize(800, 600)
        
        # Set Window Icon
        icon_path = resource_path("assets/favicon.webp")
        self.setWindowIcon(QIcon(icon_path))

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.create_dashboard_tab()
        self.create_config_tab()
        self.create_logs_tab()

        # Logging Setup
        self.setup_logging()

        # Scheduler
        self.scheduler_thread = SchedulerThread()
        self.scheduler_thread.start() # Start loop but jobs are added dynamically

    def setup_logging(self):
        handler = QtLogHandler(self.log_signal)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Attach to loggers
        logger = logging.getLogger("TanhkapayPythonProgram")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger2 = logging.getLogger("PaythonProgram")
        logger2.addHandler(handler)

        self.log_signal.connect(self.append_log)

    def append_log(self, msg):
        self.log_text.append(msg)

    def create_banner(self):
        """ Creates a banner label with the logo, fixed height 50px """
        lbl_logo = QLabel()
        lbl_logo.setFixedHeight(50)
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lbl_logo.setStyleSheet("background-color: white;") # Optional: white background for logo
        
        logo_path = resource_path("assets/logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale to height 50, keep aspect ratio
            pixmap = pixmap.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pixmap)
        else:
            lbl_logo.setText("Tanhkapay Sync Manager")
            
        return lbl_logo

    # --- Dashboard Tab ---
    def create_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Add Banner
        layout.addWidget(self.create_banner())

        # Manual Sync
        grp_manual = QGroupBox("Manual Synchronization")
        lay_manual = QVBoxLayout()
        
        self.btn_run = QPushButton("Run Sync Now")
        self.btn_run.setFixedHeight(40)
        self.btn_run.clicked.connect(self.run_manual_sync)
        lay_manual.addWidget(self.btn_run)

        self.lbl_status = QLabel("Status: Idle")
        lay_manual.addWidget(self.lbl_status)
        grp_manual.setLayout(lay_manual)
        layout.addWidget(grp_manual)

        # Scheduler
        grp_sched = QGroupBox("Automated Scheduler")
        lay_sched = QHBoxLayout()
        
        lay_sched.addWidget(QLabel("Interval (minutes):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 10080) # 1 week max
        self.spin_interval.setValue(60)
        lay_sched.addWidget(self.spin_interval)

        self.btn_start_sched = QPushButton("Start Scheduler")
        self.btn_start_sched.setCheckable(True)
        self.btn_start_sched.clicked.connect(self.toggle_scheduler)
        lay_sched.addWidget(self.btn_start_sched)
        
        grp_sched.setLayout(lay_sched)
        layout.addWidget(grp_sched)

        self.lbl_sched_status = QLabel("Scheduler Status: Stopped")
        layout.addWidget(self.lbl_sched_status)

        layout.addStretch()
        self.tabs.addTab(tab, "Dashboard")

    def run_manual_sync(self):
        self.btn_run.setEnabled(False)
        self.lbl_status.setText("Status: Running...")
        self.lbl_status.setStyleSheet("color: blue")
        
        # Run in background
        self.thread = QThread()
        self.worker = SyncWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_sync_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_sync_finished(self, result):
        self.btn_run.setEnabled(True)
        if result['success']:
            self.lbl_status.setText(f"Status: Success - {result['message']}")
            self.lbl_status.setStyleSheet("color: green")
        else:
            self.lbl_status.setText(f"Status: Failed - {result['message']}")
            self.lbl_status.setStyleSheet("color: red")

    def toggle_scheduler(self, checked):
        if checked:
            interval = self.spin_interval.value()
            schedule.clear()
            schedule.every(interval).minutes.do(lambda: self.scheduled_job())
            self.btn_start_sched.setText("Stop Scheduler")
            self.lbl_sched_status.setText(f"Scheduler Status: Active (Every {interval} min)")
            self.lbl_sched_status.setStyleSheet("color: green")
            self.spin_interval.setEnabled(False)
            logging.getLogger("TanhkapayPythonProgram").info(f"Scheduler started with {interval} min interval.")
        else:
            schedule.clear()
            self.btn_start_sched.setText("Start Scheduler")
            self.lbl_sched_status.setText("Scheduler Status: Stopped")
            self.lbl_sched_status.setStyleSheet("color: black")
            self.spin_interval.setEnabled(True)
            logging.getLogger("TanhkapayPythonProgram").info("Scheduler stopped.")

    def scheduled_job(self):
        logging.getLogger("TanhkapayPythonProgram").info("Scheduler triggering sync...")
        # Note: schedule runs in a separate thread, so run_sync blocks that thread, not UI
        # But we need to update UI carefully if needed? 
        # Actually run_sync is safe. Logging is thread-safe.
        try:
            run_sync()
        except Exception as e:
            logging.getLogger("TanhkapayPythonProgram").error(f"Scheduled sync error: {e}")

    # --- Config Tab ---
    def create_config_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Add Banner
        layout.addWidget(self.create_banner())

        form_layout = QFormLayout()
        
        self.entries = {}
        
        # --- Helper to parse legacy connection string ---
        current_conn_str = settings.get_db_connection_string() or ""
        default_server = settings.get_db_server() or ""
        default_db = settings.get_db_name() or ""
        default_user = settings.get_db_user() or ""
        default_password = settings.get_db_password() or ""
        
        if not (default_server and default_db and default_user and default_password) and "Server=" in current_conn_str:
            try:
                # Naive parsing logic for migration
                parts = current_conn_str.split(';')
                for part in parts:
                    if part.strip().lower().startswith('server='):
                        default_server = part.split('=', 1)[1]
                    elif part.strip().lower().startswith('database='):
                        default_db = part.split('=', 1)[1]
                    elif part.strip().lower().startswith('uid='):
                        default_user = part.split('=', 1)[1]
                    elif part.strip().lower().startswith('pwd='):
                        default_password = part.split('=', 1)[1]
            except Exception as e:
                logging.error(f"Failed to parse connection string: {e}")

        # --- DB Fields ---
        grp_db = QGroupBox("Database Connection")
        form_db = QFormLayout()
        
        self.entries['DB_SERVER'] = QLineEdit(default_server)
        form_db.addRow("Database Server:", self.entries['DB_SERVER'])
        
        self.entries['DB_NAME'] = QLineEdit(default_db)
        form_db.addRow("Database Name:", self.entries['DB_NAME'])
        
        self.entries['DB_USER'] = QLineEdit(default_user)
        form_db.addRow("Database Username:", self.entries['DB_USER'])
        
        self.entries['DB_PASSWORD'] = QLineEdit(default_password)
        self.entries['DB_PASSWORD'].setEchoMode(QLineEdit.EchoMode.Password)
        form_db.addRow("Database Password:", self.entries['DB_PASSWORD'])
        
        grp_db.setLayout(form_db)
        layout.addWidget(grp_db)
        
        # Test Connection Button
        btn_test_db = QPushButton("Test Database Connection")
        btn_test_db.clicked.connect(self.test_db_connection)
        layout.addWidget(btn_test_db)
        
        # --- Other Settings ---
        grp_other = QGroupBox("Other Settings")
        form_other = QFormLayout()

        # TP API URL
        self.entries['TP_API_URL'] = QLineEdit(settings.get_tp_api_url() or "")
        form_other.addRow("TP API URL:", self.entries['TP_API_URL'])

        # LOG PATH
        self.entries['LOG_PATH'] = QLineEdit(settings.get_log_path())
        form_other.addRow("LOG_PATH:", self.entries['LOG_PATH'])

        grp_other.setLayout(form_other)
        layout.addWidget(grp_other)
        
        # Log Toggle
        lbl_log = QLabel("Is Log Text Required")
        cmb_log = QComboBox()
        cmb_log.addItems(["Yes", "No"])
        current_log_setting = settings.get_log_to_file()
        cmb_log.setCurrentText("Yes" if current_log_setting else "No")
        form_layout.addRow(lbl_log, cmb_log)
        self.entries['LOG_TO_FILE'] = cmb_log
        
        layout.addLayout(form_layout)
        
        btn_save = QPushButton("Save Configuration")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Configuration")

    def save_config(self):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        env_path = os.path.join(base_path, 'config', '.env')
        try:
            # Read existing lines
            lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            new_lines = []
            updated_keys = set()
            
            # Prepare data including constructed connection string
            save_data = {}
            for key, entry in self.entries.items():
                if isinstance(entry, QComboBox):
                    save_data[key] = "True" if entry.currentText() == "Yes" else "False"
                else:
                    save_data[key] = entry.text()
            
            # Construct DB_CONNECTION_STRING
            server = save_data.get('DB_SERVER')
            db_name = save_data.get('DB_NAME')
            user = save_data.get('DB_USER')
            password = save_data.get('DB_PASSWORD')
            
            full_conn_str = settings.build_connection_string(server, db_name, user, password)
            if full_conn_str:
                save_data['DB_CONNECTION_STRING'] = full_conn_str

            # Update existing keys
            for line in lines:
                key_match = False
                for key, val in save_data.items():
                    if line.strip().startswith(f"{key}="):
                        new_lines.append(f"{key}={val}\n")
                        updated_keys.add(key)
                        key_match = True
                        break
                if not key_match:
                    new_lines.append(line)
            
            # Append missing keys
            for key, val in save_data.items():
                if key not in updated_keys:
                    if new_lines and not new_lines[-1].endswith('\n'):
                        new_lines[-1] += '\n'
                    new_lines.append(f"{key}={val}\n")
            
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
            
            # Reload
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
            QMessageBox.information(self, "Success", "Configuration saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")

    def test_db_connection(self):
        server = self.entries['DB_SERVER'].text()
        db_name = self.entries['DB_NAME'].text()
        user = self.entries['DB_USER'].text()
        password = self.entries['DB_PASSWORD'].text()
        
        if not (server and db_name and user and password):
             QMessageBox.warning(self, "Warning", "Please fill in all database fields.")
             return

        conn_str = settings.build_connection_string(server, db_name, user, password)
        
        try:
            import pyodbc
            conn = pyodbc.connect(conn_str, timeout=5)
            conn.close()
            QMessageBox.information(self, "Success", "Database connection successful!")
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to database.\nError: {e}")

    # --- Logs Tab ---
    def create_logs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Add Banner
        layout.addWidget(self.create_banner())
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: black; color: lime; font-family: Consolas;")
        layout.addWidget(self.log_text)
        
        self.tabs.addTab(tab, "Logs")
    
    def closeEvent(self, event):
        self.scheduler_thread.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
