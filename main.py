import pathlib
import tkinter as tk
import queue
import pygubu
from tkinter import BooleanVar, messagebox
from ezshare import EzShare
from config_manager import ConfigManager
from callbacks import Callbacks
from ez_share_config import EzShareConfig
from status_manager import update_status
import logging

class EzShareCPAPUI:
    def __init__(self, master=None):
        self.config_file = pathlib.Path.home() / 'config.ini'
        self.config_manager = ConfigManager(self.config_file)
        self.ezshare = EzShare()
        self.worker = None
        self.worker_queue = queue.Queue()
        self.is_running = False
        self.status_timer = None

        self.builder = pygubu.Builder()
        self.builder.add_from_file('ezsharecpap.ui')
        self.mainwindow = self.builder.get_object('mainwindow', master)
        self.builder.connect_callbacks(self)

        self.quit_var = BooleanVar()
        self.import_oscar_var = BooleanVar()

        self.builder.get_object('quitCheckbox').config(variable=self.quit_var)
        self.builder.get_object('importOscarCheckbox').config(variable=self.import_oscar_var)

        self.callbacks = Callbacks(self)
        self.ezshare_config = EzShareConfig(self)

        self.load_config()
        self.callbacks.update_checkboxes()
        self.ensure_disk_access(self.config_manager.get_setting('Settings', 'path'))
        
        logging.basicConfig(filename='application.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def update_status(self, message, message_type='info'):
        update_status(self, message, message_type)

    def reset_status(self):
        if not self.is_running:
            self.update_status('Ready.', 'info')

    def disable_ui_elements(self):
        self.builder.get_object('path').config(state=tk.DISABLED)
        self.builder.get_object('startButton').config(state=tk.DISABLED)
        self.builder.get_object('saveButton').config(state=tk.DISABLED)
        self.builder.get_object('restoreButton').config(state=tk.DISABLED)
        self.builder.get_object('quitButton').config(state=tk.DISABLED)
        self.builder.get_object('ezShareConfigBtn').config(state=tk.DISABLED)

    def enable_ui_elements(self):
        self.builder.get_object('path').config(state=tk.NORMAL)
        self.builder.get_object('startButton').config(state=tk.NORMAL)
        self.builder.get_object('saveButton').config(state=tk.NORMAL)
        self.builder.get_object('restoreButton').config(state=tk.NORMAL)
        self.builder.get_object('quitButton').config(state=tk.NORMAL)
        self.builder.get_object('ezShareConfigBtn').config(state=tk.NORMAL)

    def process_worker_queue(self):
        try:
            msg = self.worker_queue.get_nowait()
            if msg[0] == 'progress':
                self.builder.get_object('progressBar')['value'] = msg[1]
            elif msg[0] == 'status':
                self.update_status(msg[1], msg[2])
            elif msg[0] == 'finished':
                self.process_finished()
        except queue.Empty:
            pass
        if self.is_running:
            self.mainwindow.after(100, self.process_worker_queue)

    def process_finished(self):
        self.is_running = False
        self.enable_ui_elements()
        self.builder.get_object('progressBar')['value'] = 0
        if self.quit_var.get():
            self.mainwindow.quit()
        else:
            self.update_status('Ready.', 'info')
        if self.import_oscar_var.get():
            self.callbacks.import_cpap_data_with_oscar()

    def run(self):
        self.mainwindow.mainloop()

    def load_config(self):
        self.config_manager.load_config()
        self.apply_config_to_ui()

    def save_config(self, event=None):  # Updated to accept the event argument
        self.apply_ui_to_config()
        self.config_manager.save_config()
        self.update_status('Settings have been saved.', 'info')

    def apply_config_to_ui(self):
        self.builder.get_object("path").configure(path=self.config_manager.get_setting('Settings', 'path'))
        self.builder.get_object("urlEntry").delete(0, tk.END)
        self.builder.get_object("urlEntry").insert(0, self.config_manager.get_setting('Settings', 'url'))
        self.builder.get_object("ssidEntry").delete(0, tk.END)
        self.builder.get_object("ssidEntry").insert(0, self.config_manager.get_setting('WiFi', 'ssid'))
        self.builder.get_object("pskEntry").delete(0, tk.END)
        self.builder.get_object("pskEntry").insert(0, self.config_manager.get_setting('WiFi', 'psk'))
        self.quit_var.set(self.config_manager.get_setting('Settings', 'quit_after_completion') == 'True')
        self.import_oscar_var.set(self.config_manager.get_setting('Settings', 'import_oscar') == 'True')

    def apply_ui_to_config(self):
        self.config_manager.set_setting('Settings', 'path', self.builder.get_object('path').cget('path'))
        self.config_manager.set_setting('Settings', 'url', self.builder.get_object('urlEntry').get())
        self.config_manager.set_setting('WiFi', 'ssid', self.builder.get_object('ssidEntry').get())
        self.config_manager.set_setting('WiFi', 'psk', self.builder.get_object('pskEntry').get())
        self.config_manager.set_setting('Settings', 'quit_after_completion', str(self.quit_var.get()))
        self.config_manager.set_setting('Settings', 'import_oscar', str(self.import_oscar_var.get()))

    def start_process(self, event=None):
        self.callbacks.start_process(event)

    def cancel_process(self, event=None):
        self.callbacks.cancel_process(event)

    def quit_application(self, event=None):
        self.callbacks.quit_application(event)

    def open_oscar_download_page(self, event=None):
        self.callbacks.open_oscar_download_page(event)

    def restore_defaults(self, event=None):
        self.callbacks.restore_defaults(event)

    def import_cpap_data_with_oscar(self, event=None):
        self.callbacks.import_cpap_data_with_oscar(event)

    def ez_share_config(self, event=None):
        self.ezshare_config.configure_ezshare(event)

    def ensure_disk_access(self, directory):
        expanded_directory = pathlib.Path(directory).expanduser()
        if not expanded_directory.exists():
            try:
                expanded_directory.mkdir(parents=True)
            except PermissionError:
                self.request_disk_access()

    def request_disk_access(self):
        options = {'initialdir': '/'}
        directory = tk.filedialog.askdirectory(**options)
        if directory:
            self.config_manager.set_setting('Settings', 'path', directory)
            self.save_config()
            print(f"Directory selected: {directory}")
        else:
            print("No directory selected")

if __name__ == "__main__":
    app = EzShareCPAPUI()
    app.run()
