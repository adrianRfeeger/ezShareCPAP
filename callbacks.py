import pathlib
import webbrowser
import subprocess
import tkinter as tk
import logging
from worker import EzShareWorker
from utils import ensure_and_check_disk_access, check_oscar_installed, disable_ui_elements, enable_ui_elements
from status_manager import update_status, reset_status
from wifi_utils import disconnect_wifi, reset_wifi_configuration
from folder_selector import FolderSelectorDialog

class Callbacks:
    def __init__(self, app):
        self.app = app
        self.folder_selector_dialog = None
        self.buttons_active = {
            'start': True,
            'cancel': True,
            'quit': True,
            'open_oscar': True,
            'load_config': True,
            'save': True,
            'restore_defaults': True,
            'import_oscar': True,
            'select_folder': True
        }

    def _set_config(self, settings):
        logging.debug("Setting configuration: %s", settings)
        for section, items in settings.items():
            for key, value in items.items():
                self.app.config_manager.set_setting(section, key, value)

    def _validate_inputs(self):
        path = self.app.builder.get_object('local_directory_path').cget('path')
        url = self.app.builder.get_object('url_entry').get()
        ssid = self.app.builder.get_object('ssid_entry').get()

        logging.debug("Validating inputs: path=%s, url=%s, ssid=%s", path, url, ssid)

        if not path or not url or not ssid:
            update_status(self.app, 'Input Error: All fields must be filled out.', 'error')
            return False
        expanded_path = pathlib.Path(path).expanduser()
        if not ensure_and_check_disk_access(expanded_path, self.app):
            update_status(self.app, 'Invalid Path: The specified path does not exist or is not writable.', 'error')
            return False
        return True

    def start_process(self, event=None):
        logging.info("Attempting to start process.")

        try:
            # Check if the worker is already running and clean up if needed
            if self.app.worker and self.app.worker.is_alive():
                logging.warning("Previous worker thread is still running. Stopping it before starting a new process.")
                self.app.worker.stop()
                self.app.worker.join()
                logging.info("Previous worker thread stopped successfully.")

            if not self._validate_inputs():
                logging.warning("Start process aborted: Input validation failed.")
                return

            # Reset state before starting a new process
            logging.info("Resetting state before starting a new process.")
            self.app.is_running = False  # Ensure flag is reset
            self.app.ezshare.reset_state()

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

            # Additional logging before starting the worker
            if self.app.worker and self.app.worker.is_alive():
                logging.warning("Start process aborted: Previous worker thread is still running.")
                return

            logging.info("Starting new worker thread.")
            disable_ui_elements(self.app.builder)
            self.app.builder.get_object('cancel_button').config(default=tk.ACTIVE)

            # Create and name the worker thread
            self.app.worker = EzShareWorker(self.app.ezshare, self.app.worker_queue, name="EzShareWorkerThread")
            self.app.worker.start()

            # Only set is_running to True after the worker starts
            self.app.is_running = True
            logging.info("EzShareWorkerThread started successfully.")
            self.app.main_window.after(100, self.app.process_worker_queue)

        except Exception as e:
            logging.error("Error occurred during start process: %s", str(e))
            update_status(self.app, f"Error: {str(e)}", 'error')
            self.cancel_process()

    def cancel_process(self, event=None):
        logging.info("Attempting to cancel process.")
        try:
            if not self.buttons_active['cancel']:
                logging.warning("Cancel process aborted: Cancel button is not active.")
                return

            # Stop and cleanup the worker thread
            if self.app.worker and self.app.worker.is_alive():
                logging.info("Stopping running worker thread.")
                self.app.worker.stop()
                self.app.worker.join()  # Ensure the worker thread has fully terminated
                logging.info("Worker thread stopped successfully.")

            logging.info("Resetting state after cancellation.")
            self.app.worker = None
            self.app.is_running = False

            # Ensure that Wi-Fi is disconnected and resources are cleaned up
            disconnect_wifi(self.app.ezshare.ssid, self.app.ezshare.interface_name)
            reset_wifi_configuration(self.app.ezshare.interface_name)  # Ensure full cleanup of Wi-Fi configurations

            if self.folder_selector_dialog and self.folder_selector_dialog.dialog.winfo_exists():
                logging.info("Closing folder selector dialog.")
                self.folder_selector_dialog.close_dialog()

            # Explicitly reset the status using the new reset_status function
            reset_status(self.app)

            enable_ui_elements(self.app.builder)
            self.app.builder.get_object('cancel_button').config(default=tk.NORMAL)

            logging.info("Process cancelled and UI reset. Ready for new operations.")
        except Exception as e:
            logging.error("Error during process cancellation: %s", str(e))
            update_status(self.app, f"Cancellation error: {str(e)}", 'error')

    def quit_application(self, event=None):
        logging.info("Quitting application.")
        try:
            if self.app.worker and self.app.worker.is_alive():
                logging.info("Stopping running worker thread before quitting.")
                self.app.worker.stop()

            self.app.main_window.quit()
        except Exception as e:
            logging.error("Error during application quit: %s", str(e))
            update_status(self.app, f"Quit error: {str(e)}", 'error')

    def open_oscar_download_page(self, event=None):
        if not self.buttons_active['open_oscar']:
            logging.warning("Open OSCAR download page aborted: Button is not active.")
            return
        logging.info("Opening OSCAR download page.")
        webbrowser.open("https://www.sleepfiles.com/OSCAR/")

    def load_config_ui(self, event=None):
        if not self.buttons_active['load_config']:
            logging.warning("Load configuration aborted: Load button is not active.")
            return
        logging.info("Loading configuration UI.")
        self.app.load_config()

    def save_config(self, event=None):
        if not self.buttons_active['save']:
            logging.warning("Save configuration aborted: Save button is not active.")
            return
        logging.info("Saving configuration.")
        self.app.save_config(event)

    def restore_defaults(self, event=None):
        if not self.buttons_active['restore_defaults']:
            logging.warning("Restore defaults aborted: Restore defaults button is not active.")
            return
        logging.info("Restoring default settings.")
        self.app.config_manager.restore_defaults()
        self.app.load_config()
        update_status(self.app, 'Settings have been restored to defaults.', 'info')

    def update_checkboxes(self):
        logging.info("Updating checkboxes based on OSCAR installation status.")
        try:
            oscar_installed = check_oscar_installed()
            self.app.import_oscar_var.set(self.app.config_manager.get_setting('Settings', 'import_oscar') == 'True' and oscar_installed)
            self.app.builder.get_object('import_oscar_checkbox').config(state=tk.NORMAL if oscar_installed else tk.DISABLED)
            if oscar_installed:
                self.app.builder.get_object('download_oscar_link').pack_forget()
            else:
                self.app.builder.get_object('download_oscar_link').pack(fill='both', expand=True, padx=10, pady=5, side='top')
        except Exception as e:
            logging.error("Error during checkbox update: %s", str(e))
            update_status(self.app, f"Checkbox update error: {str(e)}", 'error')

    def close_event_handler(self, event=None):
        logging.info("Handling close event.")
        try:
            if self.app.worker and self.app.worker.is_alive():
                self.cancel_process()
            reset_status(self.app)  # Reset status to ready on close
            self.app.builder.get_object('progress_bar')['value'] = 0
            self.app.main_window.quit()
        except Exception as e:
            logging.error("Error during close event handling: %s", str(e))
            update_status(self.app, f"Close event error: {str(e)}", 'error')

    def open_folder_selector(self, event=None):
        if not self.buttons_active['select_folder']:
            logging.warning("Open folder selector aborted: Button is not active.")
            return

        logging.info("Opening folder selector dialog.")
        try:
            select_folder_button = self.app.builder.get_object('select_folder_button')
            select_folder_button.state(['!pressed'])
            select_folder_button.state(['!focus'])
            self.app.main_window.update_idletasks()
            disable_ui_elements(self.app.builder)
            self.folder_selector_dialog = FolderSelectorDialog(self.app.main_window, self.app)
            self.folder_selector_dialog.run()
        except Exception as e:
            logging.error("Error during folder selector opening: %s", str(e))
            update_status(self.app, f"Folder selector error: {str(e)}", 'error')

    def close_folder_selector(self):
        logging.info("Closing folder selector dialog.")
        try:
            if self.folder_selector_dialog and self.folder_selector_dialog.dialog.winfo_exists():
                self.folder_selector_dialog.close_dialog()
            enable_ui_elements(self.app.builder)
        except Exception as e:
            logging.error("Error during folder selector close: %s", str(e))
            update_status(self.app, f"Folder selector close error: {str(e)}", 'error')

    def import_cpap_data_with_oscar(self, event=None):
        if not self.buttons_active['import_oscar']:
            logging.warning("Import CPAP data with OSCAR aborted: Button is not active.")
            return

        logging.info("Importing CPAP data with OSCAR.")
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
            logging.error("Error importing CPAP data with OSCAR: %s", e)
            update_status(self.app, f"Error importing CPAP data with OSCAR: {e}", 'error')
