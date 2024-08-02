import pathlib
import webbrowser
import tkinter as tk
import subprocess
from worker import EzShareWorker
from utils import check_oscar_installed, ensure_directory_exists_and_writable
from config import save_config_ui, restore_defaults_ui, load_config

def start_process(self, event=None):
    pathchooser = self.builder.get_object('path')
    path = pathchooser.cget('path')
    url = self.builder.get_object('urlEntry').get()
    ssid = self.builder.get_object('ssidEntry').get()
    psk = self.builder.get_object('pskEntry').get()

    if not path or not url or not ssid:
        self.update_status('Input Error: All fields must be filled out.', 'error')
        return

    expanded_path = pathlib.Path(path).expanduser()
    if not ensure_directory_exists_and_writable(expanded_path):
        self.update_status('Invalid Path: The specified path does not exist or is not writable.', 'error')
        return

    self.config['Settings']['path'] = str(expanded_path)
    self.config['Settings']['url'] = url
    self.config['WiFi']['ssid'] = ssid
    self.config['WiFi']['psk'] = psk
    self.config['Settings']['quit_after_completion'] = str(self.quit_var.get())

    self.ezshare.set_params(
        path=expanded_path,
        url=url,
        start_time=None,
        show_progress=True,
        verbose=True,
        overwrite=False,
        keep_old=False,
        ssid=ssid,
        psk=psk,
        ignore=[],
        retries=3,
        connection_delay=5,
        debug=True
    )

    if self.worker and self.worker.is_alive():
        self.worker.stop()
        self.worker.join()

    self.disable_ui_elements()
    self.worker = EzShareWorker(self.ezshare, self.worker_queue)
    self.worker.start()
    self.is_running = True
    self.mainwindow.after(100, self.process_worker_queue)

def cancel_process(self, event=None):
    if self.worker and self.worker.is_alive():
        self.worker.stop()
        self.worker.join()
        self.builder.get_object('progressBar')['value'] = 0
        self.update_status('Process cancelled.', 'info')
    self.is_running = False
    self.enable_ui_elements()
    if self.ezshare:
        self.ezshare.disconnect_from_wifi()

def quit_application(self, event=None):
    if self.worker and self.worker.is_alive():
        self.worker.stop()
        self.worker.join()
    self.mainwindow.quit()

def open_oscar_download_page(self, event=None):
    webbrowser.open("https://www.sleepfiles.com/OSCAR/")

def load_config_ui(self):
    load_config(self.config, self.builder, self.quit_var, self.import_oscar_var, self.mainwindow)

def save_config(self, event=None):
    save_config_ui(self.config, self.builder, self.config_file, self.mainwindow, self.quit_var, self.import_oscar_var, self.update_status)

def restore_defaults(self, event=None):
    restore_defaults_ui(self.config, self.builder, self.quit_var, self.import_oscar_var, self.update_status)

def update_checkboxes(self):
    oscar_installed = check_oscar_installed()
    self.import_oscar_var.set(self.config['Settings'].getboolean('import_oscar', False) and oscar_installed)
    self.builder.get_object('importOscarCheckbox').config(state=tk.NORMAL if oscar_installed else tk.DISABLED)
    if oscar_installed:
        self.builder.get_object('downloadOscarLink').pack_forget()
    else:
        self.builder.get_object('downloadOscarLink').pack(fill='both', expand=True, padx=10, pady=5, side='top')

def close_event_handler(self):
    if self.worker and self.worker.is_alive():
        self.cancel_process()
    self.update_status('Ready.', 'info')
    self.builder.get_object('progressBar')['value'] = 0
    self.mainwindow.quit()

def import_cpap_data_with_oscar(self):
    script = '''
    tell application "OSCAR"
        activate
        delay 2
        tell application "System Events"
            tell process "OSCAR"
                click menu item "Import CPAP Card Data" of menu "File" of menu bar 1
            end tell
        end tell
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=True)
    except subprocess.CalledProcessError as e:
        self.update_status(f"Error importing CPAP data with OSCAR: {e}", 'error')
