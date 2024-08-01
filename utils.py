import os
import subprocess
import sys
import time
from tkinter import filedialog


def resource_path(relative_path):
    """
    Get the absolute path to the resource.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def ensure_disk_access(directory, parent):
    """
    Ensure that the specified directory exists and request access if needed.
    """
    expanded_directory = os.path.expanduser(directory)
    if not os.path.exists(expanded_directory):
        try:
            os.makedirs(expanded_directory)
        except PermissionError:
            request_disk_access(parent)


def check_disk_access(directory):
    """
    Check if the application has access to the specified directory.
    """
    expanded_directory = os.path.expanduser(directory)
    try:
        os.listdir(expanded_directory)
        return True
    except PermissionError:
        return False


def request_disk_access(parent):
    """
    Request access to the disk from the user.
    """
    options = {'initialdir': '/'}
    directory = filedialog.askdirectory(**options)
    if directory:
        parent.config['Settings']['path'] = directory
        parent.save_config()
        print(f"Directory selected: {directory}")
    else:
        print("No directory selected")


def check_oscar_installed():
    """
    Check if the OSCAR application is installed.
    """
    oscar_installed = subprocess.run(["osascript", "-e", 'id of application "OSCAR"'], capture_output=True, text=True)
    return oscar_installed.returncode == 0


def retry(func, retries=3, delay=1, backoff=2):
    """
    Retry a function with exponential backoff.

    :param func: Function to retry
    :param retries: Number of retries
    :param delay: Initial delay between retries
    :param backoff: Backoff multiplier
    :return: Result of the function if successful
    :raises: Exception if all retries fail
    """
    for i in range(retries):
        try:
            return func()
        except Exception as e:
            if i < retries - 1:
                time.sleep(delay)
                delay *= backoff
            else:
                raise e


def set_window_location(config, window):
    """
    Set the window location based on the configuration.
    """
    x = config['Window'].get('x', '100')
    y = config['Window'].get('y', '100')
    window.geometry(f'+{x}+{y}')


def save_window_location(config, window):
    """
    Save the current window location to the configuration.
    """
    x = window.winfo_x()
    y = window.winfo_y()
    config['Window'] = {
        'x': x,
        'y': y
    }
