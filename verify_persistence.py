import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Adjust path to find src/config modules
current_dir = os.path.dirname(os.path.abspath(__file__))
# Assuming this script runs from project root
sys.path.append(current_dir)

from src.qt_ui import MainWindow
from config import settings

class TestPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication only once
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Backup .env
        self.env_path = os.path.join(current_dir, 'config', '.env')
        if os.path.exists(self.env_path):
            with open(self.env_path, 'r') as f:
                self.original_env = f.read()
        else:
            self.original_env = ""

    def tearDown(self):
        # Restore .env
        with open(self.env_path, 'w') as f:
            f.write(self.original_env)

    def test_save_scheduler_auto_start(self):
        window = MainWindow()
        
        # Simulate User Actions
        window.spin_interval.setValue(15) # Change interval
        window.chk_auto_sched.setChecked(True) # Enable Auto-Start
        window.entries['START_MINIMIZED'].setChecked(True) # Enable Start Minimized
        
        # Save Config
        window.save_config()
        
        # check .env content directly
        with open(self.env_path, 'r') as f:
            content = f.read()
            
        self.assertIn("SYNC_INTERVAL=15", content)
        self.assertIn("SCHEDULER_AUTO_START=True", content)
        self.assertIn("START_MINIMIZED=True", content)
        
        print("Test Passed: Configuration saved correctly.")

if __name__ == '__main__':
    unittest.main()
