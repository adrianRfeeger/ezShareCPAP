import os
import subprocess
import sys
import time
import pathlib
import tkinter as tk
from tkinter import filedialog
from status_manager import update_status, set_status_colour, log_status

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def expand_directory_path(directory):
    return os.path.expanduser(directory)

def ensure_and_check_disk_access(directory, parent=None):
    expanded_directory = expand_directory_path(directory)
    if not os.path.exists(expanded_directory):
        if parent:
            try:
                os.makedirs(expanded_directory)
            except PermissionError:
                request_disk_access(parent)
                return False
        else:
            return False
    try:
        os.listdir(expanded_directory)
        return True
    except PermissionError:
        return False

def ensure_directory_exists_and_writable(path):
    expanded_path = pathlib.Path(path).expanduser()
    try:
        expanded_path.mkdir(parents=True, exist_ok=True)
        test_file = expanded_path / ".test_writable"
        with test_file.open('w') as f:
            f.write("test")
        test_file.unlink()
        return True
    except Exception as e:
        print(f"Error ensuring directory exists and is writable: {e}")
        return False

def request_disk_access(parent):
    options = {'initialdir': '/'}
    directory = filedialog.askdirectory(**options)
    if directory:
        parent.config_manager.set_setting('Settings', 'path', directory)
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

def disable_ui_elements(builder):
    try:
        builder.get_object('local_directory_path').config(state=tk.DISABLED)
        builder.get_object('url_entry').config(state=tk.DISABLED)
        builder.get_object('ssid_entry').config(state=tk.DISABLED)
        builder.get_object('psk_entry').config(state=tk.DISABLED)
        builder.get_object('start_button').config(state=tk.DISABLED)
        builder.get_object('save_button').config(state=tk.DISABLED)
        builder.get_object('restore_defaults_button').config(state=tk.DISABLED)
        builder.get_object('quit_button').config(state=tk.DISABLED)
        builder.get_object('configure_wifi_button').config(state=tk.DISABLED)
    except Exception as e:
        raise Exception(f"Widget not defined: {e}")

def enable_ui_elements(builder):
    try:
        builder.get_object('local_directory_path').config(state=tk.NORMAL)
        builder.get_object('url_entry').config(state=tk.NORMAL)
        builder.get_object('ssid_entry').config(state=tk.NORMAL)
        builder.get_object('psk_entry').config(state=tk.NORMAL)
        builder.get_object('start_button').config(state=tk.NORMAL)
        builder.get_object('save_button').config(state=tk.NORMAL)
        builder.get_object('restore_defaults_button').config(state=tk.NORMAL)
        builder.get_object('quit_button').config(state=tk.NORMAL)
        builder.get_object('configure_wifi_button').config(state=tk.NORMAL)
    except Exception as e:
        raise Exception(f"Widget not defined: {e}")
