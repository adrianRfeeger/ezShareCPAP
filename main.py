import pathlib
import tkinter as tk
import tkinter.ttk as ttk
import queue
import pygubu
import subprocess
import requests
import time
from wifi import reconnect_to_original_wifi, connect_to_wifi, wifi_connected
from tkinter import messagebox, BooleanVar
from ezshare import EzShare
from utils import ensure_disk_access
from config import init_config
from callbacks import (start_process, cancel_process, quit_application,
                       open_oscar_download_page, load_config_ui, save_config, restore_defaults,
                       update_checkboxes)


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
        subprocess.run(["osascript", "-e", script])

    def ez_share_config(self, event=None):
        msg = messagebox.askokcancel('ez Share Config',
                                     "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.")
        if msg:
            try:
                self.update_status('Connecting to ez Share Wi-Fi...', 'info')
                self.ezshare.set_params(
                    path=self.config['Settings']['path'],
                    url=self.config['Settings']['url'],
                    start_time=None,
                    show_progress=True,
                    verbose=True,
                    overwrite=False,
                    keep_old=False,
                    ssid=self.builder.get_object('ssidEntry').get(),
                    psk=self.builder.get_object('pskEntry').get(),
                    ignore=[],
                    retries=3,
                    connection_delay=5,  # Ensure connection_delay is set
                    debug=True
                )
                connect_to_wifi(self.ezshare)
                time.sleep(self.ezshare.connection_delay)
                if wifi_connected(self.ezshare):
                    self.update_status(f'Connected to {self.builder.get_object("ssidEntry").get()}.', 'info')
                    self.update_status('Checking if the ez Share HTTP server is reachable...', 'info')
                    try:
                        response = requests.get('http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356', timeout=5)
                        if response.status_code == 200:
                            self.update_status('HTTP server is reachable. Opening the configuration page...', 'info')
                            subprocess.run(['open', 'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356'])
                            messagebox.showinfo('Reconnect to Original Wi-Fi', 'Once configuration is complete click OK to reconnect to your original Wi-Fi network.')
                            self.update_status('Reconnecting to original Wi-Fi...', 'info')
                            success = reconnect_to_original_wifi(self.ezshare)
                            if success:
                                self.update_status('Reconnected to original Wi-Fi.', 'info')
                            else:
                                self.update_status('Failed to reconnect to original Wi-Fi. Please do so manually.', 'error')
                            self.cancel_process()  # Call cancel_process after configuration
                        else:
                            self.update_status(f'Failed to reach the HTTP server. Status code: {response.status_code}', 'error')
                    except requests.RequestException as e:
                        self.update_status(f'Failed to reach the HTTP server. Error: {e}', 'error')
                else:
                    self.update_status('Failed to connect to the ez Share Wi-Fi.', 'error')
            except RuntimeError as e:
                self.update_status(f'Error: {e}', 'error')
        else:
            self.update_status('Configuration cancelled.', 'info')

    def run(self):
        self.mainwindow.mainloop()

    # Callbacks for Pygubu commands
    def start_process(self, event=None):
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


if __name__ == "__main__":
    app = EzShareCPAPUI()
    app.run()
