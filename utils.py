import os
import subprocess
import sys
from tkinter import filedialog, messagebox

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
    options = {}
    options['initialdir'] = '/'
    directory = filedialog.askdirectory(**options)
    if directory:
        parent.config['Settings']['path'] = directory
        parent.save_config()
        print(f"Directory selected: {directory}")
    else:
        print("No directory selected")

def check_oscar_installed():
    oscar_installed = subprocess.run(["osascript", "-e", 'id of application "OSCAR"'], capture_output=True, text=True)
    return oscar_installed.returncode == 0