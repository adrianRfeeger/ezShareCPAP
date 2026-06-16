# utils.py
import os
import subprocess
import sys
import pathlib
import tkinter as tk
from tkinter import filedialog
import logging

def initialize_button_states(app):
    """
    Initialize the button states with default values in the application,
    including text fields in the main window.
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
        'download_oscar_link': {'enabled': True, 'default': True, 'visible': True},
        'local_directory_path': {'enabled': True, 'default': True, 'visible': True},
        'url_entry': {'enabled': True, 'default': True, 'visible': True},
        'ssid_entry': {'enabled': True, 'default': True, 'visible': True},
        'psk_entry': {'enabled': True, 'default': True, 'visible': True},
    }

def update_button_state(app, button_name, enabled=None, is_default=None, visible=None):
    """
    Update the state, visibility, and default status of a button or text field in the UI and its state in the global dictionary.
    """
    widget = app.builder.get_object(button_name)
    state_info = app.button_states[button_name]

    if enabled is not None:
        state_info['enabled'] = enabled
        widget.config(state=tk.NORMAL if enabled else tk.DISABLED)

    # Apply the default option only if the widget is a tk.Button
    if isinstance(widget, tk.Button) and is_default is not None:
        state_info['default'] = is_default
        widget.config(default=tk.ACTIVE if is_default else tk.NORMAL)

    if visible is not None:
        state_info['visible'] = visible
        if visible:
            widget.pack()  # Show the widget using pack()
        else:
            widget.pack_forget()  # Hide the widget using pack_forget()

    logging.info(f"Updated widget '{button_name}' - Enabled: {state_info['enabled']}, Default: {state_info.get('default')}, Visible: {state_info['visible']}")

def set_default_button_states(app):
    """
    Reset all buttons and text fields to their default states as defined in the global dictionary.
    """
    logging.info("Setting all widget states to their default values.")
    for widget_name, state_info in app.button_states.items():
        update_button_state(app, widget_name, enabled=state_info['default'], is_default=state_info['default'])

def set_process_button_states(app):
    """
    Set all buttons and text fields to their states during a major process, disabling all but the cancel button.
    """
    logging.info("Setting all widget states for a process (disabling most except the cancel button).")
    for widget_name in app.button_states:
        if widget_name == 'cancel_button':
            update_button_state(app, widget_name, enabled=True, is_default=True)
        else:
            update_button_state(app, widget_name, enabled=False, is_default=False)

def get_button_state(app, button_name):
    """
    Retrieve the current state of a button or text field from the global dictionary.

    Parameters:
    button_name (str): The name of the button or text field.

    Returns:
    dict: The current state of the button or text field.
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
    import platform
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        try:
            subprocess.run(["osascript", "-e", 'id of application "OSCAR"'], capture_output=True, text=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
    elif system == 'Windows':
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Where-Object {$_.DisplayName -match 'OSCAR'} | Select-Object -ExpandProperty DisplayName"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and 'OSCAR' in result.stdout
        except:
            # Fallback: check Program Files
            oscar_path = pathlib.Path('C:\\Program Files\\OSCAR\\OSCAR.exe')
            return oscar_path.exists()
    else:  # Linux
        try:
            subprocess.run(["which", "OSCAR"], capture_output=True, check=True, timeout=5)
            return True
        except subprocess.CalledProcessError:
            return False

def get_oscar_version():
    """
    Detect the version of OSCAR installed.

    Returns:
    str: Version string (e.g., '2.0.0', '1.7.1', 'unknown') or None if OSCAR is not installed.
    """
    import platform
    system = platform.system()
    
    if not check_oscar_installed():
        return None
    
    if system == 'Darwin':  # macOS
        return _get_oscar_version_macos()
    elif system == 'Windows':
        return _get_oscar_version_windows()
    else:  # Linux
        return _get_oscar_version_linux()

def _get_oscar_version_macos():
    """Get OSCAR version on macOS."""
    try:
        # Try to get version from OSCAR's info plist
        result = subprocess.run(
            ["mdls", "-name", "kMDItemVersion", "-raw", "/Applications/OSCAR.app"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            logging.info(f"Detected OSCAR version: {version}")
            return version
        
        # Fallback: try using osascript
        script = '''
        tell application "OSCAR"
            set oscarVersion to version
            return oscarVersion
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            logging.info(f"Detected OSCAR version: {version}")
            return version
        
        logging.warning("Could not determine OSCAR version")
        return "unknown"
    
    except subprocess.TimeoutExpired:
        logging.warning("OSCAR version detection timed out")
        return "unknown"
    except Exception as e:
        logging.error(f"Error detecting OSCAR version on macOS: {e}")
        return "unknown"

def _get_oscar_version_windows():
    """Get OSCAR version on Windows."""
    try:
        # Try registry first
        result = subprocess.run(
            ["powershell", "-Command", "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Where-Object {$_.DisplayName -match 'OSCAR'} | Select-Object -ExpandProperty DisplayVersion"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            logging.info(f"Detected OSCAR version: {version}")
            return version
        
        # Fallback: try to get version from exe
        oscar_path = pathlib.Path('C:\\Program Files\\OSCAR\\OSCAR.exe')
        if oscar_path.exists():
            result = subprocess.run(
                ["powershell", "-Command", f'(Get-Item "{oscar_path}").VersionInfo.ProductVersion'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                logging.info(f"Detected OSCAR version: {version}")
                return version
        
        logging.warning("Could not determine OSCAR version on Windows")
        return "unknown"
    
    except subprocess.TimeoutExpired:
        logging.warning("OSCAR version detection timed out")
        return "unknown"
    except Exception as e:
        logging.error(f"Error detecting OSCAR version on Windows: {e}")
        return "unknown"

def _get_oscar_version_linux():
    """Get OSCAR version on Linux."""
    try:
        result = subprocess.run(
            ["OSCAR", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            logging.info(f"Detected OSCAR version: {version}")
            return version
        
        logging.warning("Could not determine OSCAR version on Linux")
        return "unknown"
    
    except subprocess.TimeoutExpired:
        logging.warning("OSCAR version detection timed out")
        return "unknown"
    except Exception as e:
        logging.error(f"Error detecting OSCAR version on Linux: {e}")
        return "unknown"

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
