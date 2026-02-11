
import customtkinter as ctk
import os
import sys
import threading
import schedule
import time
from datetime import datetime
import logging
import queue

# Adjust path to find src/config modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Now we can import from src and config
from src.main import run_sync
from config import settings

# Setup logging capture for UI
log_queue = queue.Queue()

class QueueHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        log_queue.put(log_entry)

class SyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TankhaPay Biometric Records Synchronization")
        self.geometry("900x600")

        # Configurations
        self.base_path = self.get_application_path()
        self.env_path = os.path.join(self.base_path, 'config', '.env')
        
        # Scheduler state
        self.scheduler_running = False
        self.scheduler_thread = None
        self.stop_event = threading.Event()

        # Setup UI
        self.setup_ui()
        
        # Setup Logger to redirect to UI
        self.setup_logging_redirect()

    def get_application_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def setup_ui(self):
        # Tabs
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=20)

        self.tab_dashboard = self.tab_view.add("Dashboard")
        self.tab_config = self.tab_view.add("Configuration")
        self.tab_logs = self.tab_view.add("Logs")

        self.setup_dashboard_tab()
        self.setup_config_tab()
        self.setup_logs_tab()

    def setup_dashboard_tab(self):
        # Manual Run
        self.btn_run_now = ctk.CTkButton(self.tab_dashboard, text="Run Sync Now", command=self.run_sync_thread)
        self.btn_run_now.pack(pady=20)

        # Scheduler Controls
        self.lbl_scheduler = ctk.CTkLabel(self.tab_dashboard, text="Automated Scheduler", font=("Arial", 16, "bold"))
        self.lbl_scheduler.pack(pady=(20, 10))

        self.scheduler_frame = ctk.CTkFrame(self.tab_dashboard)
        self.scheduler_frame.pack(pady=10)

        self.lbl_interval = ctk.CTkLabel(self.scheduler_frame, text="Interval (minutes):")
        self.lbl_interval.grid(row=0, column=0, padx=10, pady=10)
        
        self.entry_interval = ctk.CTkEntry(self.scheduler_frame, width=60)
        self.entry_interval.grid(row=0, column=1, padx=10, pady=10)
        self.entry_interval.insert(0, "60")

        self.btn_start_scheduler = ctk.CTkButton(self.scheduler_frame, text="Start Scheduler", command=self.toggle_scheduler, fg_color="green")
        self.btn_start_scheduler.grid(row=0, column=2, padx=10, pady=10)

        self.lbl_status = ctk.CTkLabel(self.tab_dashboard, text="Status: Idle", text_color="gray")
        self.lbl_status.pack(pady=20)
        
        self.lbl_last_run = ctk.CTkLabel(self.tab_dashboard, text="Last Run: Never")
        self.lbl_last_run.pack(pady=5)

    def setup_config_tab(self):
        # Scrollable frame for config
        self.config_frame = ctk.CTkScrollableFrame(self.tab_config)
        self.config_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.entries = {}
        row = 0
        
        # Load current values
        configs = {
            'DB_CONNECTION_STRING': settings.get_db_connection_string() or "",
            'TP_API_URL': settings.get_tp_api_url() or "",
            'API_USERNAME': settings.get_api_username() or "",
            'API_PASSWORD': settings.get_api_password() or "",
            'LOG_PATH': settings.get_log_path(),
            'LOG_LEVEL': settings.get_log_level()
        }

        for key, value in configs.items():
            lbl = ctk.CTkLabel(self.config_frame, text=key, anchor="w")
            lbl.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
            
            entry = ctk.CTkEntry(self.config_frame, width=400)
            entry.grid(row=row+1, column=0, padx=10, pady=(0, 10), sticky="w")
            if value:
                entry.insert(0, value)
            
            self.entries[key] = entry
            row += 2

        self.btn_save = ctk.CTkButton(self.tab_config, text="Save Configuration", command=self.save_config)
        self.btn_save.pack(pady=20)

    def setup_logs_tab(self):
        self.txt_logs = ctk.CTkTextbox(self.tab_logs, width=800, height=400)
        self.txt_logs.pack(fill="both", expand=True, padx=10, pady=10)
        self.txt_logs.configure(state="disabled")

        # Periodically check log queue
        self.after(100, self.update_logs)

    def setup_logging_redirect(self):
        logger = logging.getLogger("TanhkapayPythonProgram")
        handler = QueueHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # Also catch PaythonProgram logger used in other modules
        logger2 = logging.getLogger("PaythonProgram")
        logger2.addHandler(handler)

    def update_logs(self):
        while not log_queue.empty():
            msg = log_queue.get()
            self.txt_logs.configure(state="normal")
            self.txt_logs.insert("end", msg + "\n")
            self.txt_logs.see("end")
            self.txt_logs.configure(state="disabled")
        self.after(100, self.update_logs)

    def save_config(self):
        try:
            content = ""
            for key, entry in self.entries.items():
                val = entry.get()
                content += f"{key}={val}\n"
            
            # Ensure config dir exists
            config_dir = os.path.dirname(self.env_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            with open(self.env_path, 'w') as f:
                f.write(content)
            
            # Reload env
            from dotenv import load_dotenv
            load_dotenv(self.env_path, override=True)
            
            # Since settings are functions now, they will pull fresh values from os.environ
            self.log_message("Configuration saved and reloaded.", "INFO")
        except Exception as e:
            self.log_message(f"Error saving config: {e}", "ERROR")

    def run_sync_thread(self):
        self.btn_run_now.configure(state="disabled")
        self.lbl_status.configure(text="Status: Running...", text_color="blue")
        
        thread = threading.Thread(target=self.execute_sync)
        thread.start()

    def execute_sync(self):
        self.log_message("Starting manual sync...", "INFO")
        try:
            result = run_sync()
            msg = result.get('message', 'No message')
            if result.get('success'):
                 self.log_message(f"Sync Success: {msg}", "INFO")
            else:
                 self.log_message(f"Sync Incomplete: {msg}", "WARNING")
        except Exception as e:
            self.log_message(f"Sync Failed: {e}", "ERROR")
        
        # Update UI safety via after
        self.after(0, self.finish_sync_run)

    def finish_sync_run(self):
        self.btn_run_now.configure(state="normal")
        if not self.scheduler_running:
            self.lbl_status.configure(text="Status: Idle", text_color="gray")
        else:
            interval = self.entry_interval.get()
            self.lbl_status.configure(text=f"Status: Scheduler Active (Every {interval} min)", text_color="green")
            
        self.lbl_last_run.configure(text=f"Last Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def toggle_scheduler(self):
        if self.scheduler_running:
            self.stop_scheduler()
        else:
            self.start_scheduler()

    def start_scheduler(self):
        try:
            interval = int(self.entry_interval.get())
            if interval <= 0:
                raise ValueError("Interval must be > 0")
            
            self.scheduler_running = True
            self.stop_event.clear()
            
            self.btn_start_scheduler.configure(text="Stop Scheduler", fg_color="red")
            self.entry_interval.configure(state="disabled")
            self.lbl_status.configure(text=f"Status: Scheduler Active (Every {interval} min)", text_color="green")
            
            self.log_message(f"Scheduler started with interval {interval} minutes.", "INFO")
            
            schedule.clear()
            schedule.every(interval).minutes.do(self.scheduler_job)
            
            self.scheduler_thread = threading.Thread(target=self.run_scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
        except ValueError:
            self.log_message("Invalid interval. Please enter a positive integer.", "ERROR")

    def stop_scheduler(self):
        self.scheduler_running = False
        self.stop_event.set()
        
        self.btn_start_scheduler.configure(text="Start Scheduler", fg_color="green")
        self.entry_interval.configure(state="normal")
        self.lbl_status.configure(text="Status: Idle", text_color="gray")
        self.log_message("Scheduler stopped.", "INFO")

    def run_scheduler_loop(self):
        while self.scheduler_running and not self.stop_event.is_set():
            schedule.run_pending()
            time.sleep(1)

    def scheduler_job(self):
        self.log_message("Scheduler initiating sync...", "INFO")
        # Use execute_sync but we need to be careful about threading.
        # execute_sync spawns `run_sync` which is blocking IO.
        # Here we are already in a thread. We can call run_sync directly or define a method that doesn't spawn another thread if we don't want to.
        # But `run_sync` is just the function logic. `run_sync_thread` spawns a thread.
        # We can just call the logic.
        try:
             result = run_sync()
             msg = result.get('message', 'No message')
             level = "INFO" if result.get('success') else "WARNING"
             self.log_message(f"Scheduled Run Result: {msg}", level)
             # Update last run label safely
             self.after(0, lambda: self.lbl_last_run.configure(text=f"Last Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        except Exception as e:
             self.log_message(f"Scheduled Run Failed: {e}", "ERROR")

    def log_message(self, message, level="INFO"):
        # Put into queue for UI
        log_queue.put(f"{datetime.now().strftime('%H:%M:%S')} - {level} - {message}")

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = SyncApp()
    app.mainloop()
