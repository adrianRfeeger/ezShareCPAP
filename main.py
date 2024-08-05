import pathlib
import tkinter as tk
import queue
import logging
import pygubu
from tkinter import BooleanVar
from ezshare import ezShare
from config_manager import ConfigManager
from callbacks import Callbacks
from ez_share_config import EzShareConfig
from status_manager import update_status
from utils import ensure_and_check_disk_access, disable_ui_elements, enable_ui_elements, resource_path
from folder_selector import FolderSelectorDialog  # Import FolderSelectorDialog

class EzShareCPAPUI:
    def __init__(self, master=None):
        self.config_file = pathlib.Path.home() / 'config.ini'
        self.config_manager = ConfigManager(self.config_file)
        self.ezshare = ezShare()
        self.worker = None
        self.worker_queue = queue.Queue()
        self.is_running = False
        self.status_timer = None
        self.quitting = False  # Add a quitting flag

        self.builder = pygubu.Builder()
        self.builder.add_from_file(resource_path('ezsharecpap.ui'))
        self.main_window = self.builder.get_object('main_window', master)
        self.builder.connect_callbacks(self)

        icon_path = resource_path('icon.png')
        self.main_window.iconphoto(False, tk.PhotoImage(file=icon_path))

        self.quit_var = BooleanVar()
        self.import_oscar_var = BooleanVar()

        self.builder.get_object('quit_checkbox').config(variable=self.quit_var)
        self.builder.get_object('import_oscar_checkbox').config(variable=self.import_oscar_var)

        self.callbacks = Callbacks(self)
        self.ezshare_config = EzShareConfig(self)

        self.load_config()
        self.callbacks.update_checkboxes()
        ensure_and_check_disk_access(self.config_manager.get_setting('Settings', 'path'))
        
        logging.basicConfig(filename='application.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

        # Add a method to open the folder selector
        self.builder.get_object('folderselectorButton').config(command=self.open_folder_selector)

    def disable_ui_elements(self):
        logging.debug("Disabling UI elements")
        self.callbacks.buttons_active = {key: False for key in self.callbacks.buttons_active}
        disable_ui_elements(self.builder)
        self.builder.get_object('cancel_button').config(default=tk.ACTIVE)

    def enable_ui_elements(self):
        logging.debug("Enabling UI elements")
        self.callbacks.buttons_active = {key: True for key in self.callbacks.buttons_active}
        enable_ui_elements(self.builder)
        self.builder.get_object('cancel_button').config(default=tk.NORMAL)

    def update_status(self, message, message_type='info'):
        logging.debug(f"Attempting to update status to '{message}' with type '{message_type}'")
        update_status(self, message, message_type)

    def reset_status(self):
        logging.debug(f"Checking if status should be reset to 'Ready.' (is_running={self.is_running})")
        if not self.is_running:
            logging.info("Resetting status to 'Ready.'")
            self.update_status('Ready.', 'info')

    def process_worker_queue(self):
        try:
            msg = self.worker_queue.get_nowait()
            if msg[0] == 'progress':
                self.builder.get_object('progress_bar')['value'] = msg[1]
            elif msg[0] == 'status':
                self.update_status(msg[1], msg[2])
            elif msg[0] == 'finished':
                self.process_finished()
        except queue.Empty:
            pass
        if self.is_running:
            self.main_window.after(100, self.process_worker_queue)

    def process_finished(self):
        logging.info("Process finished")
        self.is_running = False
        self.enable_ui_elements()
        self.builder.get_object('progress_bar')['value'] = 0
        if self.quit_var.get():
            self.main_window.quit()
        else:
            self.update_status('Ready.', 'info')
        if self.import_oscar_var.get():
            self.callbacks.import_cpap_data_with_oscar()

    def run(self):
        logging.info("Starting main application loop")
        self.main_window.mainloop()

    def load_config(self):
        try:
            self.config_manager.load_config()
            self.apply_config_to_ui()
        except Exception as e:
            logging.error(f"Error loading config: {e}")

    def save_config(self, event=None):
        if not self.callbacks.buttons_active['save']:
            return
        try:
            self.apply_ui_to_config()
            self.config_manager.save_config()
            self.update_status('Settings have been saved.', 'info')
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def apply_config_to_ui(self):
        self.builder.get_object("local_directory_path").configure(path=self.config_manager.get_setting('Settings', 'path'))
        self.builder.get_object("url_entry").delete(0, tk.END)
        self.builder.get_object("url_entry").insert(0, self.config_manager.get_setting('Settings', 'url'))
        self.builder.get_object("ssid_entry").delete(0, tk.END)
        self.builder.get_object("ssid_entry").insert(0, self.config_manager.get_setting('WiFi', 'ssid'))
        self.builder.get_object("psk_entry").delete(0, tk.END)
        self.builder.get_object("psk_entry").insert(0, self.config_manager.get_setting('WiFi', 'psk'))
        self.quit_var.set(self.config_manager.get_setting('Settings', 'quit_after_completion') == 'True')
        self.import_oscar_var.set(self.config_manager.get_setting('Settings', 'import_oscar') == 'True')

    def apply_ui_to_config(self):
        self.config_manager.set_setting('Settings', 'path', self.builder.get_object('local_directory_path').cget('path'))
        self.config_manager.set_setting('Settings', 'url', self.builder.get_object('url_entry').get())
        self.config_manager.set_setting('WiFi', 'ssid', self.builder.get_object('ssid_entry').get())
        self.config_manager.set_setting('WiFi', 'psk', self.builder.get_object('psk_entry').get())
        self.config_manager.set_setting('Settings', 'quit_after_completion', str(self.quit_var.get()))
        self.config_manager.set_setting('Settings', 'import_oscar', str(self.import_oscar_var.get()))

    def start_process(self, event=None):
        logging.debug("Starting process")
        self.is_running = True
        self.callbacks.start_process(event)

    def cancel_process(self, event=None):
        logging.debug("Cancelling process")
        self.callbacks.cancel_process(event)

    def quit_application(self, event=None):
        logging.debug("Quitting application")
        self.quitting = True  # Set quitting flag
        if self.worker and self.worker.is_alive():
            logging.debug("Stopping worker thread before quitting")
            self.worker_queue.put(('quit',))  # Tell the worker thread to quit
        if self.main_window:
            logging.debug("Destroying main window")
            self.main_window.destroy()

    def open_oscar_download_page(self, event=None):
        self.callbacks.open_oscar_download_page(event)

    def restore_defaults(self, event=None):
        self.callbacks.restore_defaults(event)
    
    def open_folder_selector(self, event=None):
        logging.debug("Opening folder selector")
        # Create and open the folder selector dialog
        folder_selector_dialog = FolderSelectorDialog(self.main_window, self)
        folder_selector_dialog.run()

    def import_cpap_data_with_oscar(self, event=None):
        self.callbacks.import_cpap_data_with_oscar(event)

    def ez_share_config(self, event=None):
        logging.debug("Configuring ezShare")
        self.is_running = True
        self.ezshare_config.configure_ezshare(event)

if __name__ == "__main__":
    app = EzShareCPAPUI()
    app.run()
