import os
import subprocess
import sys
import pathlib
import tkinter as tk
from tkinter import filedialog
import logging

# Global dictionary to keep track of button states
button_states = {
    'start_button': {'enabled': True, 'is_default': True},
    'cancel_button': {'enabled': False, 'is_default': False},
    'quit_button': {'enabled': True, 'is_default': False},
    'save_button': {'enabled': True, 'is_default': False},
    'restore_defaults_button': {'enabled': True, 'is_default': False},
    'import_oscar_checkbox': {'enabled': True, 'is_default': False},
    'quit_checkbox': {'enabled': True, 'is_default': False},
    'select_folder_button': {'enabled': True, 'is_default': False},
    'configure_wifi_button': {'enabled': True, 'is_default': False},
    'local_directory_path': {'enabled': True, 'is_default': False}
}

def update_button_state(app, button_name, enabled=True, is_default=False, visible=True):
    """
    Update the state, visibility, and default status of a button in the UI and its state in the global dictionary.

    Parameters:
    app (tk.Widget): The main application object that contains the UI components.
    button_name (str): The name of the button widget.
    enabled (bool): Whether the button should be enabled or disabled.
    is_default (bool): Whether the button should be set as the default button.
    visible (bool): Whether the button should be visible or hidden.
    """
    button = app.builder.get_object(button_name)

    # Update the button state in the UI
    if enabled:
        button.config(state=tk.NORMAL)
    else:
        button.config(state=tk.DISABLED)

    # Apply the default option only if the widget is a Button
    if isinstance(button, tk.Button):
        if is_default:
            button.config(default=tk.ACTIVE)
        else:
            button.config(default=tk.NORMAL)

    if visible:
        button.pack()  # Show the button using pack()
    else:
        button.pack_forget()  # Hide the button using pack_forget()

    # Update the global state dictionary
    button_states[button_name] = {'enabled': enabled, 'is_default': is_default}
    logging.info(f"Updated button '{button_name}' - Enabled: {enabled}, Default: {is_default}, Visible: {visible}")

def set_button_states(app, states):
    """
    Set the states of multiple buttons at once.

    Parameters:
    app (tk.Widget): The main application object that contains the UI components.
    states (dict): A dictionary where keys are button names and values are dicts with 'enabled' and 'is_default' keys.
    """
    for button_name, state_info in states.items():
        update_button_state(app, button_name, enabled=state_info['enabled'], is_default=state_info['is_default'])

def set_default_button_states(app):
    """
    Reset all buttons to their default states as defined in the global dictionary.
    """
    logging.info("Setting all button states to their default values.")
    set_button_states(app, button_states)

def set_process_button_states(app):
    """
    Set all buttons to their states during a major process, disabling all but the cancel button.
    """
    process_button_states = {
        'start_button': {'enabled': False, 'is_default': False},
        'cancel_button': {'enabled': True, 'is_default': True},
        'quit_button': {'enabled': False, 'is_default': False},
        'save_button': {'enabled': False, 'is_default': False},
        'restore_defaults_button': {'enabled': False, 'is_default': False},
        'import_oscar_checkbox': {'enabled': False, 'is_default': False},
        'quit_checkbox': {'enabled': False, 'is_default': False},
        'select_folder_button': {'enabled': False, 'is_default': False},
        'configure_wifi_button': {'enabled': False, 'is_default': False},
        'local_directory_path': {'enabled': False, 'is_default': False}
    }
    logging.info("Setting all button states for a process (disabling most except the cancel button).")
    set_button_states(app, process_button_states)

def get_button_state(button_name):
    """
    Retrieve the current state of a button from the global dictionary.

    Parameters:
    button_name (str): The name of the button.

    Returns:
    dict: The current state of the button.
    """
    return button_states.get(button_name, {'enabled': False, 'is_default': False})

def ensure_and_check_disk_access(directory, parent=None):
    """
    Ensure the specified directory exists and is accessible.

    Parameters:
    directory (str): The directory path to check.
    parent (tk.Widget): The parent widget (optional).

    Returns:
    bool: True if the directory exists and is accessible, False otherwise.
    """
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
    """
    Request access to a directory if the current one is inaccessible.

    Parameters:
    parent (tk.Widget): The parent widget.
    """
    options = {'initialdir': '/'}
    directory = filedialog.askdirectory(**options)
    if directory:
        parent.config_manager.set_setting('Settings', 'path', directory)
        parent.save_config()
        print(f"Directory selected: {directory}")
    else:
        print("No directory selected")

def check_oscar_installed():
    """
    Check if the OSCAR application is installed.

    Returns:
    bool: True if OSCAR is installed, False otherwise.
    """
    try:
        oscar_installed = subprocess.run(["osascript", "-e", 'id of application "OSCAR"'], capture_output=True, text=True, check=True)
        return oscar_installed.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error checking OSCAR installation: {e}")
        return False

def resource_path(relative_path):
    """
    Get the absolute path to the resource, works for dev and for PyInstaller.

    Parameters:
    relative_path (str): The relative path to the resource.

    Returns:
    str: The absolute path to the resource.
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
