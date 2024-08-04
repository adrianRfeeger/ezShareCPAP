import pathlib
import webbrowser
import tkinter as tk
import subprocess
from worker import EzShareWorker
from utils import ensure_and_check_disk_access, check_oscar_installed, disable_ui_elements, enable_ui_elements
from status_manager import update_status
from wifi_utils import disconnect_from_wifi
from folder_selector import FolderSelector

class Callbacks:
    def __init__(self, app):
        self.app = app
        self.buttons_active = {
            'start': True,
            'cancel': True,
            'quit': True,
            'open_oscar': True,
            'load_config': True,
            'save': True,
            'restore_defaults': True,
            'import_oscar': True
        }

    def _set_config(self, settings):
        for section, items in settings.items():
            for key, value in items.items():
                self.app.config_manager.set_setting(section, key, value)

    def _validate_inputs(self):
        path = self.app.builder.get_object('local_directory_path').cget('path')
        url = self.app.builder.get_object('url_entry').get()
        ssid = self.app.builder.get_object('ssid_entry').get()
        if not path or not url or not ssid:
            update_status(self.app, 'Input Error: All fields must be filled out.', 'error')
            return False
        expanded_path = pathlib.Path(path).expanduser()
        if not ensure_and_check_disk_access(expanded_path, self.app):
            update_status(self.app, 'Invalid Path: The specified path does not exist or is not writable.', 'error')
            return False
        return True

    def start_process(self, event=None):
        if not self.buttons_active['start']:
            return

        if not self._validate_inputs():
            return

        pathchooser = self.app.builder.get_object('local_directory_path')
        path = pathchooser.cget('path')
        url = self.app.builder.get_object('url_entry').get()
        ssid = self.app.builder.get_object('ssid_entry').get()
        psk = self.app.builder.get_object('psk_entry').get()

        expanded_path = pathlib.Path(path).expanduser()
        settings = {
            'Settings': {'path': str(expanded_path), 'url': url, 'quit_after_completion': str(self.app.quit_var.get())},
            'WiFi': {'ssid': ssid, 'psk': psk}
        }
        self._set_config(settings)

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

        disable_ui_elements(self.app.builder)
        self.app.builder.get_object('cancel_button').config(default=tk.ACTIVE)
        self.app.worker = EzShareWorker(self.app.ezshare, self.app.worker_queue)
        self.app.worker.start()
        self.app.is_running = True
        self.app.main_window.after(100, self.app.process_worker_queue)

    def cancel_process(self, event=None):
        if not self.buttons_active['cancel']:
            return

        if self.app.worker and self.app.worker.is_alive():
            self.app.worker.stop()
            self.app.worker.join()
            self.app.builder.get_object('progress_bar')['value'] = 0
        update_status(self.app, 'Process cancelled.', 'info')
        self.app.is_running = False
        enable_ui_elements(self.app.builder)
        self.app.builder.get_object('cancel_button').config(default=tk.NORMAL)
        disconnect_from_wifi(self.app.ezshare)
        update_status(self.app, 'Ready.', 'info')

    def quit_application(self, event=None):
        if not self.buttons_active['quit']:
            return

        if self.app.worker and self.app.worker.is_alive():
            self.app.worker.stop()
            self.app.worker.join()
        self.app.main_window.quit()

    def open_oscar_download_page(self, event=None):
        if not self.buttons_active['open_oscar']:
            return
        webbrowser.open("https://www.sleepfiles.com/OSCAR/")

    def load_config_ui(self, event=None):
        if not self.buttons_active['load_config']:
            return
        self.app.load_config()

    def save_config(self, event=None):
        if not self.buttons_active['save']:
            return
        self.app.save_config(event)

    def restore_defaults(self, event=None):
        if not self.buttons_active['restore_defaults']:
            return
        self.app.config_manager.restore_defaults()
        self.app.load_config()
        update_status(self.app, 'Settings have been restored to defaults.', 'info')

    def update_checkboxes(self):
        oscar_installed = check_oscar_installed()
        self.app.import_oscar_var.set(self.app.config_manager.get_setting('Settings', 'import_oscar') == 'True' and oscar_installed)
        self.app.builder.get_object('import_oscar_checkbox').config(state=tk.NORMAL if oscar_installed else tk.DISABLED)
        if oscar_installed:
            self.app.builder.get_object('download_oscar_link').pack_forget()
        else:
            self.app.builder.get_object('download_oscar_link').pack(fill='both', expand=True, padx=10, pady=5, side='top')

    def close_event_handler(self, event=None):
        if self.app.worker and self.app.worker.is_alive():
            self.cancel_process()
        update_status(self.app, 'Ready.', 'info')
        self.app.builder.get_object('progress_bar')['value'] = 0
        self.app.main_window.quit()
    

    def open_folder_selector(self, event=None):
        folder_selector = FolderSelector(self.app)
        folder_selector.run()

    def import_cpap_data_with_oscar(self, event=None):
        if not self.buttons_active['import_oscar']:
            return

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
