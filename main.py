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
from utils import ensure_and_check_disk_access, resource_path

class EzShareCPAPUI:
    def __init__(self, master=None):
        # Define the location for the plist file in the Preferences folder
        self.config_file = pathlib.Path.home() / 'Library' / 'Preferences' / 'com.ezShareCPAP.config.plist'

        # Initialize ConfigManager with the plist file
        self.config_manager = ConfigManager(self.config_file)
        self.ezshare = ezShare()
        self.worker = None
        self.worker_queue = queue.Queue()
        self.is_running = False
        self.status_timer = None

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

        # Initialize button states
        self.button_states = {
            'start_button': True,
            'cancel_button': False,  # Initially disabled
            'quit_button': True,
            'download_oscar_link': True,
            'save_button': True,
            'restore_defaults_button': True,
            'select_folder_button': True,
            'configure_wifi_button': True
        }

        # Configure buttons with their commands
        self.builder.get_object('start_button').config(command=lambda: self.handle_button_click('start_button', self.callbacks.start_process))
        self.builder.get_object('cancel_button').config(command=lambda: self.handle_button_click('cancel_button', self.callbacks.cancel_process))
        self.builder.get_object('quit_button').config(command=lambda: self.handle_button_click('quit_button', self.callbacks.quit_application))
        self.builder.get_object('save_button').config(command=lambda: self.handle_button_click('save_button', self.callbacks.save_config))
        self.builder.get_object('restore_defaults_button').config(command=lambda: self.handle_button_click('restore_defaults_button', self.callbacks.restore_defaults))
        self.builder.get_object('select_folder_button').config(command=lambda: self.handle_button_click('select_folder_button', self.callbacks.open_folder_selector))
        self.builder.get_object('configure_wifi_button').config(command=lambda: self.handle_button_click('configure_wifi_button', self.ez_share_config))

        # Bind the label (not a button) with an event
        self.builder.get_object('download_oscar_link').bind("<Button-1>", lambda event: self.handle_button_click('download_oscar_link', self.callbacks.open_oscar_download_page))

        self.load_config()
        self.callbacks.update_checkboxes()
        ensure_and_check_disk_access(self.config_manager.get_setting('Settings', 'path'))
        
        logging.basicConfig(filename='application.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def handle_button_click(self, button_name, action):
        if self.button_states.get(button_name, False):
            action()
        else:
            logging.info(f"Button '{button_name}' is disabled and was clicked.")

    def enable_button(self, button_name):
        self.button_states[button_name] = True
        self.builder.get_object(button_name).config(state=tk.NORMAL)

    def disable_button(self, button_name):
        self.button_states[button_name] = False
        self.builder.get_object(button_name).config(state=tk.DISABLED)

    def enable_ui_elements(self):
        for button in self.button_states:
            self.enable_button(button)

    def disable_ui_elements(self):
        for button in self.button_states:
            self.disable_button(button)

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
            pass  # No message to process, continue normally

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
        if not self.button_states['save_button']:
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
        self.is_running = True
        self.callbacks.start_process(event)

    def cancel_process(self, event=None):
        self.callbacks.cancel_process(event)

    def quit_application(self, event=None):
        self.callbacks.quit_application(event)

    def open_oscar_download_page(self, event=None):
        self.callbacks.open_oscar_download_page(event)

    def restore_defaults(self, event=None):
        self.callbacks.restore_defaults(event)
    
    def open_folder_selector(self, event=None):
        self.callbacks.open_folder_selector(event)

    def import_cpap_data_with_oscar(self, event=None):
        self.callbacks.import_cpap_data_with_oscar(event)

    def ez_share_config(self, event=None):
        self.is_running = True
        self.ezshare_config.configure_ezshare(event)

if __name__ == "__main__":
    app = EzShareCPAPUI()
    app.run()
