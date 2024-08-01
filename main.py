import pathlib
import tkinter as tk
import queue
import pygubu
from tkinter import BooleanVar
from ezshare import EzShare
from utils import ensure_disk_access
from config import init_config
from callbacks import (start_process, cancel_process, quit_application,
                       open_oscar_download_page, import_cpap_data_with_oscar, load_config_ui, save_config, restore_defaults,
                       update_checkboxes)
from ez_share_config import ez_share_config


class EzShareCPAPUI:
    def __init__(self, master=None):
        self.config_file = pathlib.Path.home() / 'config.ini'
        self.config = init_config(self.config_file)
        self.ezshare = EzShare()
        self.worker = None
        self.worker_queue = queue.Queue()
        self.is_running = False
        self.status_timer = None

        # Initialize the Pygubu builder and UI
        self.builder = pygubu.Builder()
        self.builder.add_from_file('ezshare.ui')
        self.mainwindow = self.builder.get_object('mainwindow', master)
        self.builder.connect_callbacks(self)

        # Initialize BooleanVars for checkbuttons
        self.quit_var = BooleanVar()
        self.import_oscar_var = BooleanVar()

        # Link BooleanVars to checkbuttons
        self.builder.get_object('quitCheckbox').config(variable=self.quit_var)
        self.builder.get_object('importOscarCheckbox').config(variable=self.import_oscar_var)

        # Initialize the configuration and UI
        load_config_ui(self)
        update_checkboxes(self)
        ensure_disk_access(self.config['Settings']['path'], self)

    def update_status(self, message, message_type='info'):
        current_status = self.builder.get_object('statusLabel')['text']
        if message != current_status:
            self.builder.get_object('statusLabel')['text'] = message
            if message_type == 'error':
                self.builder.get_object('statusLabel')['foreground'] = 'red'
            else:
                self.builder.get_object('statusLabel').config(foreground='')
            if message_type == 'info' and message != 'Ready.':
                self.status_timer = self.mainwindow.after(5000, self.reset_status)

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
            self.import_cpap_data_with_oscar()

    def run(self):
        self.mainwindow.mainloop()

    # Callbacks for Pygubu commands
    def start_process(self, event=None):
        self.is_running = True
        start_process(self, event)

    def cancel_process(self, event=None):
        cancel_process(self, event)

    def quit_application(self, event=None):
        quit_application(self, event)

    def open_oscar_download_page(self, event=None):
        open_oscar_download_page(self, event)

    def load_config_ui(self, event=None):
        load_config_ui(self)

    def save_config(self, event=None):
        save_config(self, event)

    def restore_defaults(self, event=None):
        restore_defaults(self, event)

    def import_cpap_data_with_oscar(self, event=None):
        import_cpap_data_with_oscar(self, event)
    
    def ez_share_config(self, event=None):
        ez_share_config(self, event)

if __name__ == "__main__":
    app = EzShareCPAPUI()
    app.run()
