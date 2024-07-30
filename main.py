#!/usr/bin/python3
import pathlib
import tkinter as tk
import tkinter.ttk as ttk
import queue
import requests
import subprocess
import time
import webbrowser
import pygubu
from tkinter import messagebox, BooleanVar
from ezshare import ezShare
from worker import EzShareWorker
from wifi import connect_to_wifi, wifi_connected, disconnect_from_wifi
from utils import check_oscar_installed, ensure_disk_access, resource_path
from project_styles import setup_ttk_styles
from config import init_config, save_config

PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "ezshare.ui"
RESOURCE_PATHS = [PROJECT_PATH]


class ezShareCPAPUI:
    def __init__(self, master=None, on_first_object_cb=None):
        self.config_file = pathlib.Path.home() / 'ezshare_config.ini'
        self.config = init_config(self.config_file)
        self.ezshare = ezShare()
        self.worker = None
        self.worker_queue = queue.Queue()
        self.is_running = False
        self.status_timer = None

        # Initialize the pygubu builder
        self.builder = pygubu.Builder(on_first_object=on_first_object_cb)
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(PROJECT_UI)
        
        # Create the main window
        self.mainwindow = self.builder.get_object('mainwindow', master)
        self.builder.connect_callbacks(self)
        
        # Apply custom styles
        setup_ttk_styles(self.mainwindow)
        
        # Initialize BooleanVars for checkbuttons
        self.quit_var = BooleanVar()
        self.import_oscar_var = BooleanVar()

        # Link BooleanVars to checkbuttons
        self.builder.get_object('quitCheckbox').config(variable=self.quit_var)
        self.builder.get_object('importOscarCheckbox').config(variable=self.import_oscar_var)

        # Find the downloadOscarLink label and bind it
        self.download_label = self.builder.get_object('downloadOscarLink')
        self.download_label.bind("<Button-1>", self.open_oscar_download_page)

        # Initialize the configuration and UI
        self.load_config()
        self.update_checkboxes()
        ensure_disk_access(self.config['Settings']['path'], self)

        # Bind the quit button to the quit_application method
        self.builder.get_object('quitBtn').config(command=self.quit_application)

    def run(self):
        self.mainwindow.mainloop()

    def load_config(self):
        self.config.read(self.config_file)
        pathchooser = self.builder.get_object('path')
        pathchooser.configure(path=self.config['Settings'].get('path', '~/Documents/CPAP_Data/SD_card'))
        self.builder.get_object('urlEntry').insert(0, self.config['Settings'].get('url', 'http://192.168.4.1/dir?dir=A:'))
        self.builder.get_object('ssidEntry').insert(0, self.config['WiFi'].get('ssid', 'ez Share'))
        self.builder.get_object('pskEntry').insert(0, self.config['WiFi'].get('psk', '88888888'))
        self.quit_var.set(self.config['Settings'].getboolean('quit_after_completion', False))
        self.import_oscar_var.set(self.config['Settings'].getboolean('import_oscar', False))
        self.apply_window_geometry()

    def save_config(self, event=None):
        pathchooser = self.builder.get_object('path')
        self.config['Settings'] = {
            'path': pathchooser.cget('path'),
            'url': self.builder.get_object('urlEntry').get(),
            'accessibility_checked': self.config['Settings'].get('accessibility_checked', 'False'),
            'accessibility_prompt_disabled': self.config['Settings'].get('accessibility_prompt_disabled', 'False'),
            'import_oscar': str(self.import_oscar_var.get()),
            'quit_after_completion': str(self.quit_var.get())
        }
        self.config['WiFi'] = {
            'ssid': self.builder.get_object('ssidEntry').get(),
            'psk': self.builder.get_object('pskEntry').get()
        }
        self.save_window_geometry()
        save_config(self.config, self.config_file)
        self.update_status('Settings have been saved.', 'info')

    def save_window_geometry(self):
        width = self.mainwindow.winfo_width()
        height = self.mainwindow.winfo_height()
        x = self.mainwindow.winfo_x()
        y = self.mainwindow.winfo_y()
        self.config['Window'] = {
            'width': width,
            'height': height,
            'x': x,
            'y': y
        }

    def apply_window_geometry(self):
        width = self.config['Window'].get('width', '800')
        height = self.config['Window'].get('height', '600')
        x = self.config['Window'].get('x', '100')
        y = self.config['Window'].get('y', '100')
        self.mainwindow.geometry(f'{width}x{height}+{x}+{y}')

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
        if not expanded_path.is_dir():
            self.update_status('Invalid Path: The specified path does not exist or is not a directory.', 'error')
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

    def process_worker_queue(self, event=None):
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

    def update_status(self, message, message_type='info'):
        current_status = self.builder.get_object('statusLabel')['text']
        if message != current_status:
            self.builder.get_object('statusLabel')['text'] = message
            if message_type == 'error':
                self.builder.get_object('statusLabel')['foreground'] = 'red'
            else:
                self.builder.get_object('statusLabel')['foreground'] = 'black'
            if message_type == 'info' and message != 'Ready.':
                self.status_timer = self.mainwindow.after(5000, self.reset_status)

    def reset_status(self):
        if not self.is_running:
            self.update_status('Ready.', 'info')

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

    def close_event_handler(self):
        if self.worker and self.worker.is_alive():
            self.cancel_process()
        self.update_status('Ready.', 'info')
        self.builder.get_object('progressBar')['value'] = 0
        self.mainwindow.quit()

    def ez_share_config(self, event=None):
        msg = messagebox.askokcancel('ez Share Config',
                                     "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.")
        if msg:
            try:
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
                    connection_delay=5,
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

    def closeEvent(self, event):
        self.close_event_handler()
        event.accept()

    def restore_defaults(self, event=None):
        default_path = '~/Documents/CPAP_Data/SD_card'
        default_url = 'http://192.168.4.1/dir?dir=A:'
        default_ssid = 'ez Share'
        default_psk = '88888888'

        self.config['Settings'] = {
            'path': default_path,
            'url': default_url,
            'accessibility_checked': 'False',
            'accessibility_prompt_disabled': 'False',
            'import_oscar': 'False',
            'quit_after_completion': 'False'
        }
        self.config['WiFi'] = {
            'ssid': default_ssid,
            'psk': default_psk
        }
        self.config['Window'] = {
            'width': '800',
            'height': '600',
            'x': '100',
            'y': '100'
        }

        # Clear and update the TextEdit fields with default values
        path_field = self.builder.get_object("path")
        path_field.configure(path=default_path)

        url_entry = self.builder.get_object("urlEntry")
        url_entry.delete(0, tk.END)
        url_entry.insert(0, default_url)

        ssid_entry = self.builder.get_object("ssidEntry")
        ssid_entry.delete(0, tk.END)
        ssid_entry.insert(0, default_ssid)

        psk_entry = self.builder.get_object("pskEntry")
        psk_entry.delete(0, tk.END)
        psk_entry.insert(0, default_psk)

        # Use the BooleanVar objects to update checkboxes
        self.quit_var.set(False)
        self.import_oscar_var.set(False)

        self.update_status('Settings have been restored to defaults.', 'info')

    def update_checkboxes(self):
        oscar_installed = check_oscar_installed()
        self.import_oscar_var.set(self.config['Settings'].getboolean('import_oscar', False) and oscar_installed)
        self.builder.get_object('importOscarCheckbox').config(state=tk.NORMAL if oscar_installed else tk.DISABLED)
        if oscar_installed:
            self.builder.get_object('downloadOscarLink').pack_forget()
        else:
            self.builder.get_object('downloadOscarLink').pack(fill='both', expand=True, padx=10, pady=5, side='top')

    def disable_ui_elements(self):
        self.builder.get_object('path').config(state=tk.DISABLED)
        self.builder.get_object('startBtn').config(state=tk.DISABLED)
        self.builder.get_object('saveBtn').config(state=tk.DISABLED)
        self.builder.get_object('defaultBtn').config(state=tk.DISABLED)
        self.builder.get_object('quitBtn').config(state=tk.DISABLED)
        self.builder.get_object('ezShareConfigBtn').config(state=tk.DISABLED)

    def enable_ui_elements(self):
        self.builder.get_object('path').config(state=tk.NORMAL)
        self.builder.get_object('startBtn').config(state=tk.NORMAL)
        self.builder.get_object('saveBtn').config(state=tk.NORMAL)
        self.builder.get_object('defaultBtn').config(state=tk.NORMAL)
        self.builder.get_object('quitBtn').config(state=tk.NORMAL)
        self.builder.get_object('ezShareConfigBtn').config(state=tk.NORMAL)

    def quit_application(self, event=None):
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self.worker.join()
        self.mainwindow.quit()

    def open_oscar_download_page(self, event=None):
        webbrowser.open("https://www.sleepfiles.com/OSCAR/")


if __name__ == "__main__":
    app = ezShareCPAPUI()
    app.run()
