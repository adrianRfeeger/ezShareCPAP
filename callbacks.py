import pathlib
import webbrowser
import subprocess
import tkinter as tk
import logging
import queue
import time
import sys

from worker import EzShareWorker
from utils import ensure_and_check_disk_access, check_oscar_installed
from status_manager import update_status, reset_status
from wifi_utils import disconnect_wifi, reset_wifi_configuration
from folder_selector import FolderSelectorDialog

class Callbacks:
    def __init__(self, app):
        self.app = app
        self.folder_selector_dialog = None
        self.last_cancel_time = 0  # Initialize last cancel time for delay

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
        if not self.app.button_states['start_button']:
            logging.info("Start process aborted: Start button is not enabled.")
            return

        logging.info("Attempting to start process.")
        self.app.is_running = True  # Ensure the "Ready" status is suppressed

        if time.time() - self.last_cancel_time < 2:  # 2-second delay
            logging.info("Waiting for cleanup to complete before restarting.")
            return

        try:
            # Disable all buttons except the cancel button
            self.app.disable_ui_elements()
            self.app.update_button_state('cancel_button', True)

            # Check if the worker is already running and clean up if needed
            if self.app.worker and self.app.worker.is_alive():
                logging.warning("Previous worker thread is still running. Stopping it before starting a new process.")
                self.app.worker.stop()
                self.app.worker.join()
                logging.info("Previous worker thread stopped successfully.")

            # Reset state before starting a new process
            logging.info("Resetting state before starting a new process.")
            self.app.is_running = False  # Ensure flag is reset
            self.app.ezshare.reset_state()

            if not self._validate_inputs():
                logging.warning("Start process aborted: Input validation failed.")
                # Re-enable UI elements since validation failed
                self.app.enable_ui_elements()
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

            # Clear any remaining items in the worker queue
            while not self.app.worker_queue.empty():
                try:
                    self.app.worker_queue.get_nowait()
                except queue.Empty:
                    break

            # Create and start the worker thread
            logging.info("Starting new worker thread.")
            self.app.worker = EzShareWorker(self.app.ezshare, self.app.worker_queue, name="EzShareWorkerThread")
            self.app.worker.start()

            # Only set is_running to True after the worker starts
            self.app.is_running = True
            logging.info("EzShareWorkerThread started successfully.")
            self.app.main_window.after(100, self.app.process_worker_queue)

        except Exception as e:
            logging.error(f"Error occurred during start process: {str(e)}")
            update_status(self.app, f"Error: {str(e)}", 'error')
            self.cancel_process()

    def cancel_process(self, event=None):
        if not self.app.button_states['cancel_button']:
            logging.info("Cancel process aborted: Cancel button is not enabled.")
            return

        logging.info("Attempting to cancel process.")
        try:
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
            if self.app.ezshare.interface_name:
                disconnect_wifi(self.app.ezshare.ssid, self.app.ezshare.interface_name)
                reset_wifi_configuration(self.app.ezshare.interface_name)
            else:
                logging.info("No active Wi-Fi connection to disconnect, or process was canceled before connection.")

            # Mark the cancel button as inactive and disable it
            self.app.update_button_state('cancel_button', False)

            # Re-enable all other UI elements after cancellation
            self.app.enable_ui_elements()

            self.app.builder.get_object('progress_bar')['value'] = 0

            logging.info("Process cancelled and UI reset. Ready for new operations.")
            update_status(self.app, 'The process was cancelled by the user.', 'info')
        except Exception as e:
            logging.error(f"Error during process cancellation: {str(e)}")
            update_status(self.app, f"Cancellation error: {str(e)}", 'error')
        finally:
            self.last_cancel_time = time.time()  # Update the last cancel time

    def process_finished(self):
        logging.info("Process finished")
        self.app.is_running = False

        # Re-enable UI elements after the process is finished
        self.app.enable_ui_elements()
        self.app.builder.get_object('progress_bar')['value'] = 0

        # Disable the cancel button
        self.app.update_button_state('cancel_button', False)

        if self.app.quit_var.get():
            self.app.main_window.quit()
        else:
            self.update_status('Ready.', 'info')
        if self.app.import_oscar_var.get():
            self.import_cpap_data_with_oscar()

    def quit_application(self, event=None):
        if not self.app.button_states['quit_button']:
            logging.info("Quit application aborted: Quit button is not enabled.")
            return

        logging.info("Quitting application.")
        try:
            # Ensure the cancel process is called to stop any ongoing operations
            self.cancel_process()

            # Force quit the application
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error during application quit: {str(e)}")
            update_status(self.app, f"Quit error: {str(e)}", 'error')
        finally:
            logging.info("Application has been quit.")

    def open_oscar_download_page(self, event=None):
        if not self.app.button_states['download_oscar_link']:
            logging.warning("Open OSCAR download page aborted: Button is not enabled.")
            return
        logging.info("Opening OSCAR download page.")
        webbrowser.open("https://www.sleepfiles.com/OSCAR/")

    def save_config(self, event=None):
        if not self.app.button_states['save_button']:
            logging.warning("Save configuration aborted: Save button is not enabled.")
            return
        logging.info("Saving configuration.")
        try:
            self.apply_ui_to_config()
            self.app.config_manager.save_config()
            self.app.update_status('Settings have been saved.', 'info')
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            self.app.update_status(f'Error saving settings: {e}', 'error')  # Notify user of the error

    def apply_ui_to_config(self):
        self.app.config_manager.set_setting('Settings', 'path', self.app.builder.get_object('local_directory_path').cget('path'))
        self.app.config_manager.set_setting('Settings', 'url', self.app.builder.get_object('url_entry').get())
        self.app.config_manager.set_setting('WiFi', 'ssid', self.app.builder.get_object('ssid_entry').get())
        self.app.config_manager.set_setting('WiFi', 'psk', self.app.builder.get_object('psk_entry').get())
        self.app.config_manager.set_setting('Settings', 'quit_after_completion', bool(self.app.quit_var.get()))  # Ensure Boolean
        self.app.config_manager.set_setting('Settings', 'import_oscar', bool(self.app.import_oscar_var.get()))    # Ensure Boolean

    def restore_defaults(self, event=None):
        if not self.app.button_states['restore_defaults_button']:
            logging.warning("Restore defaults aborted: Restore defaults button is not enabled.")
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
            logging.error(f"Error during checkbox update: {str(e)}")
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
            logging.error(f"Error during close event handling: {str(e)}")
            update_status(self.app, f"Close event error: {str(e)}", 'error')

    def open_folder_selector(self, event=None):
        if not self.app.button_states['select_folder_button']:
            logging.warning("Open folder selector aborted: Button is not enabled.")
            return

        logging.info("Opening folder selector dialog.")
        try:
            # Disable all buttons except the cancel button
            self.app.disable_ui_elements()
            self.app.update_button_state('cancel_button', True)

            select_folder_button = self.app.builder.get_object('select_folder_button')
            select_folder_button.state(['!pressed'])
            select_folder_button.state(['!focus'])
            self.app.main_window.update_idletasks()
            self.folder_selector_dialog = FolderSelectorDialog(self.app.main_window, self.app)
            self.folder_selector_dialog.run()
        except Exception as e:
            logging.error(f"Error during folder selector opening: {str(e)}")
            update_status(self.app, f"Folder selector error: {str(e)}", 'error')

    def close_folder_selector(self):
        if not self.app.button_states['cancel_button']:
            logging.warning("Close folder selector aborted: Cancel button is not enabled.")
            return

        logging.info("Closing folder selector dialog.")
        try:
            if self.folder_selector_dialog and self.folder_selector_dialog.dialog.winfo_exists():
                self.folder_selector_dialog.close_dialog()
            
            # Disable the cancel button after closing the dialog
            self.app.update_button_state('cancel_button', False)
            
            self.app.enable_ui_elements()
        except Exception as e:
            logging.error(f"Error during folder selector close: {str(e)}")
            update_status(self.app, f"Folder selector close error: {str(e)}", 'error')

    def import_cpap_data_with_oscar(self, event=None):
        if not self.app.button_states['import_oscar_checkbox']:
            logging.warning("Import CPAP data with OSCAR aborted: Button is not enabled.")
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
            logging.error(f"Error importing CPAP data with OSCAR: {e}")
            update_status(self.app, f"Error importing CPAP data with OSCAR: {e}", 'error')
