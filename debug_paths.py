
import sys
import os

def print_paths():
    print(f"sys.executable: {sys.executable}")
    print(f"sys.frozen: {getattr(sys, 'frozen', False)}")
    
    if getattr(sys, 'frozen', False):
         base_path = os.path.dirname(sys.executable)
    else:
         base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
         
    env_path = os.path.join(base_path, 'config', '.env')
    print(f"Calculated env_path: {env_path}")
    print(f"Exists: {os.path.exists(env_path)}")
    
    try:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                print("--- Content ---")
                print(f.read())
                print("--- End Content ---")
    except Exception as e:
        print(f"Error reading: {e}")

if __name__ == "__main__":
    print_paths()
