
import sys
import os

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.qt_ui import main

if __name__ == "__main__":
    main()
