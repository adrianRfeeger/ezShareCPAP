import pathlib
import webbrowser
import tkinter as tk
import subprocess
from worker import EzShareWorker
from utils import check_oscar_installed, ensure_directory_exists_and_writable, update_status

class Callbacks:
    def __init__(self, app):
        self.app = app

    def start_process(self, event=None):
        pathchooser = self.app.builder.get_object('path')
        path = pathchooser.cget('path')
        url = self.app.builder.get_object('urlEntry').get()
        ssid = self.app.builder.get_object('ssidEntry').get()
        psk = self.app.builder.get_object('pskEntry').get()

        if not path or not url or not ssid:
            update_status(self.app, 'Input Error: All fields must be filled out.', 'error')
            return

        expanded_path = pathlib.Path(path).expanduser()
        if not ensure_directory_exists_and_writable(expanded_path):
            update_status(self.app, 'Invalid Path: The specified path does not exist or is not writable.', 'error')
            return

        self.app.config_manager.set_setting('Settings', 'path', str(expanded_path))
        self.app.config_manager.set_setting('Settings', 'url', url)
        self.app.config_manager.set_setting('WiFi', 'ssid', ssid)
        self.app.config_manager.set_setting('WiFi', 'psk', psk)
        self.app.config_manager.set_setting('Settings', 'quit_after_completion', str(self.app.quit_var.get()))

        self.app.ezshare.set_params(
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

        if self.app.worker and self.app.worker.is_alive():
            self.app.worker.stop()
            self.app.worker.join()

        self.app.disable_ui_elements()
        self.app.worker = EzShareWorker(self.app.ezshare, self.app.worker_queue)
        self.app.worker.start()
        self.app.is_running = True
        self.app.mainwindow.after(100, self.app.process_worker_queue)

    def cancel_process(self, event=None):
        if self.app.worker and self.app.worker.is_alive():
            self.app.worker.stop()
            self.app.worker.join()
            self.app.builder.get_object('progressBar')['value'] = 0
            update_status(self.app, 'Process cancelled.', 'info')
        self.app.is_running = False
        self.app.enable_ui_elements()
        if self.app.ezshare:
            self.app.ezshare.disconnect_from_wifi()

    def quit_application(self, event=None):
        if self.app.worker and self.app.worker.is_alive():
            self.app.worker.stop()
            self.app.worker.join()
        self.app.mainwindow.quit()

    def open_oscar_download_page(self, event=None):
        webbrowser.open("https://www.sleepfiles.com/OSCAR/")

    def load_config_ui(self, event=None):  # Updated to accept the event argument
        self.app.load_config()

    def save_config(self, event=None):  # Updated to accept the event argument
        self.app.save_config(event)

    def restore_defaults(self, event=None):
        self.app.config_manager.restore_defaults()
        self.app.load_config()
        update_status(self.app, 'Settings have been restored to defaults.', 'info')

    def update_checkboxes(self):
        oscar_installed = check_oscar_installed()
        self.app.import_oscar_var.set(self.app.config_manager.get_setting('Settings', 'import_oscar') == 'True' and oscar_installed)
        self.app.builder.get_object('importOscarCheckbox').config(state=tk.NORMAL if oscar_installed else tk.DISABLED)
        if oscar_installed:
            self.app.builder.get_object('downloadOscarLink').pack_forget()
        else:
            self.app.builder.get_object('downloadOscarLink').pack(fill='both', expand=True, padx=10, pady=5, side='top')

    def close_event_handler(self, event=None):  # Updated to accept the event argument
        if self.app.worker and self.app.worker.is_alive():
            self.cancel_process()
        update_status(self.app, 'Ready.', 'info')
        self.app.builder.get_object('progressBar')['value'] = 0
        self.app.mainwindow.quit()

    def import_cpap_data_with_oscar(self, event=None):  # Updated to accept the event argument
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
            update_status(self.app, f"Error importing CPAP data with OSCAR: {e}", 'error')
