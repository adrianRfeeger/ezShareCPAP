import os
import subprocess
import sys
import pathlib
import tkinter as tk
from tkinter import filedialog
import logging

import tkinter as tk
import logging

def initialize_button_states(app):
    """
    Initialize the button states with default values in the application.
    """
    app.button_states = {
        'start_button': {'enabled': True, 'default': True, 'visible': True},
        'cancel_button': {'enabled': False, 'default': False, 'visible': True},
        'quit_button': {'enabled': True, 'default': True, 'visible': True},
        'save_button': {'enabled': True, 'default': True, 'visible': True},
        'restore_defaults_button': {'enabled': True, 'default': True, 'visible': True},
        'import_oscar_checkbox': {'enabled': True, 'default': True, 'visible': True},
        'quit_checkbox': {'enabled': True, 'default': True, 'visible': True},
        'select_folder_button': {'enabled': True, 'default': True, 'visible': True},
        'configure_wifi_button': {'enabled': True, 'default': True, 'visible': True},
        'local_directory_path': {'enabled': True, 'default': True, 'visible': True}
    }

def update_button_state(app, button_name, enabled=None, is_default=None, visible=None):
    """
    Update the state, visibility, and default status of a button in the UI and its state in the global dictionary.
    """
    button = app.builder.get_object(button_name)
    state_info = app.button_states[button_name]

    if enabled is not None:
        state_info['enabled'] = enabled
        button.config(state=tk.NORMAL if enabled else tk.DISABLED)

    # Apply the default option only if the widget is a tk.Button
    if isinstance(button, tk.Button) and is_default is not None:
        state_info['default'] = is_default
        button.config(default=tk.ACTIVE if is_default else tk.NORMAL)

    if visible is not None:
        state_info['visible'] = visible
        if visible:
            button.pack()  # Show the button using pack()
        else:
            button.pack_forget()  # Hide the button using pack_forget()

    logging.info(f"Updated button '{button_name}' - Enabled: {state_info['enabled']}, Default: {state_info.get('default')}, Visible: {state_info['visible']}")

def set_default_button_states(app):
    """
    Reset all buttons to their default states as defined in the global dictionary.
    """
    logging.info("Setting all button states to their default values.")
    for button_name, state_info in app.button_states.items():
        update_button_state(app, button_name, enabled=state_info['default'], is_default=state_info['default'])

def set_process_button_states(app):
    """
    Set all buttons to their states during a major process, disabling all but the cancel button.
    """
    logging.info("Setting all button states for a process (disabling most except the cancel button).")
    for button_name in app.button_states:
        if button_name == 'cancel_button':
            update_button_state(app, button_name, enabled=True, is_default=True)
        else:
            update_button_state(app, button_name, enabled=False, is_default=False)

def get_button_state(app, button_name):
    """
    Retrieve the current state of a button from the global dictionary.

    Parameters:
    button_name (str): The name of the button.

    Returns:
    dict: The current state of the button.
    """
    return app.button_states.get(button_name, {'enabled': False, 'default': False, 'visible': True})

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
