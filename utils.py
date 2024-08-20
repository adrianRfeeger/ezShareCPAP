import os
import subprocess
import sys
import pathlib
import tkinter as tk
from tkinter import filedialog

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def ensure_and_check_disk_access(directory, parent=None):
    expanded_directory = pathlib.Path(directory).expanduser()
    if not expanded_directory.exists():
        if parent:
            try:
                expanded_directory.mkdir(parents=True)
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
        builder.get_object('select_folder_button').config(state=tk.DISABLED)
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
        builder.get_object('select_folder_button').config(state=tk.NORMAL)
    except Exception as e:
        raise Exception(f"Widget not defined: {e}")
