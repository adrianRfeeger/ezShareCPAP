import os
import subprocess
import sys
import time
from tkinter import filedialog

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def ensure_disk_access(directory, parent):
    expanded_directory = os.path.expanduser(directory)
    if not os.path.exists(expanded_directory):
        try:
            os.makedirs(expanded_directory)
        except PermissionError:
            request_disk_access(parent)

def check_disk_access(directory):
    expanded_directory = os.path.expanduser(directory)
    try:
        os.listdir(expanded_directory)
        return True
    except PermissionError:
        return False

def request_disk_access(parent):
    options = {'initialdir': '/'}
    directory = filedialog.askdirectory(**options)
    if directory:
        parent.config['Settings']['path'] = directory
        parent.save_config()
        print(f"Directory selected: {directory}")
    else:
        print("No directory selected")

def check_oscar_installed():
    try:
        oscar_installed = subprocess.run(["osascript", "-e", 'id of application "OSCAR"'], capture_output=True, text=True, check=True)
        return oscar_installed.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error checking OSCAR installation: {e}")
        return False

def retry(func, retries=3, delay=1, backoff=2):
    for i in range(retries):
        try:
            return func()
        except Exception as e:
            if i < retries - 1:
                time.sleep(delay)
                delay *= backoff
            else:
                raise e

def ensure_directory_exists_and_writable(path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".test_writable"
        with test_file.open('w') as f:
            f.write("test")
        test_file.unlink()
        return True
    except Exception as e:
        print(f"Error ensuring directory exists and is writable: {e}")
        return False
