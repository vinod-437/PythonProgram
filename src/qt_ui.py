import sys
import os
import threading
import schedule
import time
import logging
import hashlib
from datetime import datetime

# Adjust path to find src/config modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTabWidget, 
                             QLineEdit, QFormLayout, QTextEdit, QMessageBox, 
                             QSpinBox, QGroupBox, QComboBox, QSystemTrayIcon, QMenu, QCheckBox, QDialog, QDialogButtonBox, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot, QTimer
# Import QIcon and QPixmap
from PyQt6.QtGui import QIcon, QPixmap, QAction
import winreg

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
# logging.info(f"Loading environment from: {env_path}") # Moved to __init__
load_dotenv(env_path, override=True)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

    return os.path.join(base_path, relative_path)

def set_auto_start(enable: bool):
    """ Adds or removes the application from Windows Startup Registry """
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "TanhkapaySync"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        
        if enable:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                # Quote path to handle spaces
                cmd = f'"{exe_path}"'
                # If we want to start minimized, we might need a flag, but for now just start updates
                # We can check env var at startup to decide whether to show window
            else:
                 # Logic for python script (less critical for end user but good for dev)
                 python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                 script_path = os.path.abspath(__file__)
                 # Entry point is run_gui.py usually
                 base = os.path.dirname(os.path.dirname(script_path))
                 script = os.path.join(base, "run_gui.py")
                 cmd = f'"{python_exe}" "{script}"'

            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass # Already disabled
                
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logging.error(f"Failed to update registry: {e}")
        return False
        
def check_auto_start():
    """ Checks if auto-start is enabled in registry """
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "TanhkapaySync"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

        return False

class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Authentication Required")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Please enter the application password:")
        layout.addWidget(lbl)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
    def get_password(self):
        return self.password_input.text()

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
        
        # Window Sizing and Centering
        screen = self.screen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Set Width to 50% of screen, Height to 60% (looks good ratio)
        new_width = int(screen_width * 0.5)
        new_height = int(screen_height * 0.6)
        
        self.resize(new_width, new_height)
        
        # Center the window
        qr = self.frameGeometry()
        cp = screen_geometry.center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
        # Set Window Icon
        icon_path = resource_path("assets/favicon.webp")
        self.setWindowIcon(QIcon(icon_path))

        # Main Layout - Using Stacked Widget for Locked vs Unlocked Views
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # --- Locked View ---
        self.locked_widget = QWidget()
        self.setup_locked_view()
        self.central_stack.addWidget(self.locked_widget)

        # --- Unlocked View ---
        self.unlocked_widget = QWidget()
        self.setup_unlocked_view()
        self.central_stack.addWidget(self.unlocked_widget)
        
        # Initialize Login State
        self.is_logged_in = settings.get_is_logged_in()
        
        # Apply Initial State
        self.toggle_auth_state(self.is_logged_in)

        # Logging
        self.setup_logging()

        # System Tray
        self.setup_system_tray()

        # Scheduler
        self.scheduler_thread = SchedulerThread()
        self.scheduler_thread.start() # Start loop but jobs are added dynamically

        # Log startup paths for debugging
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(base_dir, 'config', '.env')
        logger = logging.getLogger("TanhkapayPythonProgram")
        logger.info(f"Startup: sys.executable: {sys.executable}")
        logger.info(f"Startup: Base Dir: {base_dir}")
        logger.info(f"Startup: Expected .env path: {env_file}")
        logger.info(f"Startup: .env exists: {os.path.exists(env_file)}")

    def setup_locked_view(self):
        layout = QVBoxLayout(self.locked_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Centered Logo
        logo_label = self.create_banner_large()
        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Password Input Container
        input_container = QWidget()
        # Responsive width: roughly 50% of the window width, but clamped
        input_container.setMinimumWidth(300)
        input_container.setMaximumWidth(500) 
        
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_instruction = QLabel("Enter Application Password")
        lbl_instruction.setStyleSheet("color: gray; font-size: 14px;")
        input_layout.addWidget(lbl_instruction)

        self.txt_password_login = QLineEdit()
        self.txt_password_login.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password_login.setPlaceholderText("Password")
        self.txt_password_login.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;")
        self.txt_password_login.returnPressed.connect(self.handle_direct_login)
        input_layout.addWidget(self.txt_password_login)
        
        # Error Label
        self.lbl_login_error = QLabel("")
        self.lbl_login_error.setStyleSheet("color: red; font-size: 12px;")
        self.lbl_login_error.hide()
        input_layout.addWidget(self.lbl_login_error)

        layout.addWidget(input_container, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch() # Push everything up a bit if needed, or keep centered

    def setup_unlocked_view(self):
        layout = QVBoxLayout(self.unlocked_widget)
        
        # Header (Logo + Logout)
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout.addWidget(self.create_banner())
        
        self.btn_logout = QPushButton("Logout")
        self.btn_logout.setFixedWidth(100)
        self.btn_logout.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")
        self.btn_logout.clicked.connect(self.handle_logout)
        header_layout.addWidget(self.btn_logout, alignment=Qt.AlignmentFlag.AlignRight)
        
        layout.addWidget(header_widget)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.create_dashboard_tab()
        self.create_config_tab()
        self.create_logs_tab()

    def create_banner_large(self):
        """ Creates a larger banner label for the locked screen """
        lbl_logo = QLabel()
        # lbl_logo.setFixedHeight(80) 
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_path = resource_path("assets/logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale to height 80
            pixmap = pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pixmap)
        else:
            lbl_logo.setText("<h1>Tanhkapay Sync Manager</h1>")
            lbl_logo.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
            
        return lbl_logo

    def handle_direct_login(self):
        input_pass = self.txt_password_login.text()
        app_password = settings.get_app_password()
        
        if not app_password:
            # No password set, allow
            self.toggle_auth_state(True)
            return

        input_hash = hashlib.md5(input_pass.encode()).hexdigest()
        
        if input_hash == app_password or input_pass == app_password:
            self.lbl_login_error.hide()
            self.txt_password_login.clear()
            self.toggle_auth_state(True)
        else:
            self.lbl_login_error.setText("Incorrect password.")
            self.lbl_login_error.show()
            self.txt_password_login.selectAll()

    def handle_logout(self):
        self.toggle_auth_state(False)

    def toggle_auth_state(self, is_logged_in):
        self.is_logged_in = is_logged_in
        self.update_login_state(is_logged_in)
        
        if is_logged_in:
            self.central_stack.setCurrentWidget(self.unlocked_widget)
        else:
            self.central_stack.setCurrentWidget(self.locked_widget)
            self.txt_password_login.setFocus()

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = resource_path("assets/favicon.webp")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback if no icon
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        # Context Menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.attempt_show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Connect double click to show
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.attempt_show()

    def attempt_show(self):
        # Just show the window. The window content is now protected by tabs visibility.
        self.show()
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.activateWindow()

    def closeEvent(self, event):
        if settings.get_minimize_to_tray():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Tanhkapay Sync",
                "Application minimized to tray. Right-click icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self.scheduler_thread.stop()
            event.accept()

    def setup_logging(self):
        handler = QtLogHandler(self.log_signal)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Attach to loggers
        logger = logging.getLogger("TanhkapayPythonProgram")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Also log to file for debugging
        log_path = settings.get_log_path()
        if not os.path.exists(log_path):
            os.makedirs(log_path)
            
        file_handler = logging.FileHandler(os.path.join(log_path, "debug_gui.log"))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger2 = logging.getLogger("PaythonProgram")
        logger2.addHandler(handler)
        logger2.addHandler(file_handler)

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
        # Add Banner - Removed
        # layout.addWidget(self.create_banner())

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
        self.spin_interval.setRange(1, 10080) # 1 week max
        self.spin_interval.setValue(settings.get_sync_interval())
        lay_sched.addWidget(self.spin_interval)

        # Auto-Start Scheduler Checkbox
        self.chk_auto_sched = QCheckBox("Auto-start Scheduler on App Launch")
        self.chk_auto_sched.setChecked(settings.get_scheduler_auto_start())
        lay_sched.addWidget(self.chk_auto_sched)

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
        # Add Banner - Removed
        # layout.addWidget(self.create_banner())

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

        # --- Application Settings ---
        grp_app = QGroupBox("Application Settings")
        lay_app = QVBoxLayout()
        
        # Run on Startup
        self.chk_startup = QCheckBox("Run on Windows Startup")
        self.chk_startup.setChecked(check_auto_start())
        lay_app.addWidget(self.chk_startup)
        
        # Start Minimized
        self.entries['START_MINIMIZED'] = QCheckBox("Start Minimized in Tray")
        self.entries['START_MINIMIZED'].setChecked(settings.get_start_minimized())
        lay_app.addWidget(self.entries['START_MINIMIZED'])
        
        # Minimize to Tray
        self.entries['MINIMIZE_TO_TRAY'] = QCheckBox("Minimize to Tray on Close")
        self.entries['MINIMIZE_TO_TRAY'].setChecked(settings.get_minimize_to_tray())
        lay_app.addWidget(self.entries['MINIMIZE_TO_TRAY'])
        
        # App Password
        lay_pass = QHBoxLayout()
        lay_pass.addWidget(QLabel("App Password:"))
        self.entries['APP_PASSWORD'] = QLineEdit()
        self.entries['APP_PASSWORD'].setPlaceholderText("Enter new password to change (leave empty to keep)")
        self.entries['APP_PASSWORD'].setEchoMode(QLineEdit.EchoMode.Password)
        lay_pass.addWidget(self.entries['APP_PASSWORD'])
        lay_app.addLayout(lay_pass)
        
        grp_app.setLayout(lay_app)
        layout.addWidget(grp_app)
        
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
        logging.getLogger("TanhkapayPythonProgram").info(f"Saving configuration to: {env_path}")
        try:
            # Handle Registry for Startup
            startup_enabled = self.chk_startup.isChecked()
            if not set_auto_start(startup_enabled):
                QMessageBox.warning(self, "Registry Error", "Failed to update Startup registry key. Try running as Admin.")

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
                if key == 'APP_PASSWORD':
                    continue # Handle separately
                if isinstance(entry, QComboBox):
                    save_data[key] = "True" if entry.currentText() == "Yes" else "False"
                elif isinstance(entry, QCheckBox):
                    save_data[key] = "True" if entry.isChecked() else "False"
                else:
                    save_data[key] = entry.text()
            
            # Handle Password
            new_pass = self.entries['APP_PASSWORD'].text()
            if new_pass:
                # Hash it
                hashed = hashlib.md5(new_pass.encode()).hexdigest()
                save_data['APP_PASSWORD'] = hashed
            
            # Save Scheduler Auto-Start
            
            # Save Scheduler Auto-Start
            save_data['SCHEDULER_AUTO_START'] = "True" if self.chk_auto_sched.isChecked() else "False"
            
            # Save Sync Interval from Dashboard tab
            save_data['SYNC_INTERVAL'] = str(self.spin_interval.value())
            
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
        # Add Banner - Removed
        # layout.addWidget(self.create_banner())
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: black; color: lime; font-family: Consolas;")
        layout.addWidget(self.log_text)
        
        self.tabs.addTab(tab, "Logs")

    def update_login_state(self, is_logged_in):
        """ Updates only the IS_LOGGED_IN key in .env """
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        env_path = os.path.join(base_path, 'config', '.env')
        
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            new_lines = []
            key_found = False
            val_str = "True" if is_logged_in else "False"
            
            for line in lines:
                if line.strip().startswith("IS_LOGGED_IN="):
                    new_lines.append(f"IS_LOGGED_IN={val_str}\n")
                    key_found = True
                else:
                    new_lines.append(line)
            
            if not key_found:
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines[-1] += '\n'
                new_lines.append(f"IS_LOGGED_IN={val_str}\n")
                
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
                
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
            
        except Exception as e:
            logging.error(f"Failed to update login state: {e}")

    
    
    


def setup_global_logging():
    log_path = settings.get_log_path()
    if not os.path.exists(log_path):
        try:
            os.makedirs(log_path)
        except Exception:
            pass
            
    log_file = os.path.join(log_path, "debug_gui.log")
    
    # Configure root logger to write to file
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def verify_password_logic(parent=None):
    """
    Prompts for password if set. 
    Returns True if valid (or no password set), False if cancelled/incorrect.
    """
    app_password = settings.get_app_password()
    if not app_password:
        return True # No password set
        
    dlg = PasswordDialog(parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        input_pass = dlg.get_password()
        input_hash = hashlib.md5(input_pass.encode()).hexdigest()
        
        if input_hash == app_password:
            return True
        elif input_pass == app_password:
            return True # Legacy
        else:
            QMessageBox.critical(parent, "Access Denied", "Incorrect password.")
            return False
    else:
        return False # Cancelled

def main():
    # Setup logging immediately
    setup_global_logging()
    logging.info("Application starting...")
    
    app = QApplication(sys.argv)
    
    # Check for password protection - REMOVED for persistent login logic
    # logging.info("Verifying password on startup...")
    # if not verify_password_logic(None):
    #     logging.info("Password verification failed or cancelled. Exiting.")
    #     sys.exit(0)

    # Check if we should start minimized
    start_minimized = settings.get_start_minimized()
    
    window = MainWindow()
    
    # Apply initial scheduler state if auto-start is enabled
    if settings.get_scheduler_auto_start():
        window.btn_start_sched.setChecked(True)
        window.toggle_scheduler(True)
        
    if start_minimized:
        # Don't show the window, just the tray
        # But we need to ensure the tray icon is visible (it is set up in __init__)
        logging.info("Application started minimized to tray.")
    else:
        window.show()
        
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
