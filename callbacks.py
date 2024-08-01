import pathlib
import webbrowser
import tkinter as tk
import requests
import subprocess
import time
from tkinter import messagebox
from ezshare import EzShare
from worker import EzShareWorker
from utils import ensure_disk_access, check_oscar_installed
from config import save_config_ui, restore_defaults_ui, load_config
from wifi import reconnect_to_original_wifi, connect_to_wifi, wifi_connected
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


def quit_application(self, event=None):
    if self.worker and self.worker.is_alive():
        self.worker.stop()
        self.worker.join()
    self.mainwindow.quit()


def open_oscar_download_page(self, event=None):
    webbrowser.open("https://www.sleepfiles.com/OSCAR/")


def load_config_ui(self):
    load_config(self.config, self.builder, self.quit_var, self.import_oscar_var, self.mainwindow)


def save_config(self, event=None):
    save_config_ui(self.config, self.builder, self.config_file, self.mainwindow, self.quit_var, self.import_oscar_var, self.update_status)


def restore_defaults(self, event=None):
    restore_defaults_ui(self.config, self.builder, self.quit_var, self.import_oscar_var, self.update_status)


def update_checkboxes(self):
    oscar_installed = check_oscar_installed()
    self.import_oscar_var.set(self.config['Settings'].getboolean('import_oscar', False) and oscar_installed)
    self.builder.get_object('importOscarCheckbox').config(state=tk.NORMAL if oscar_installed else tk.DISABLED)
    if oscar_installed:
        self.builder.get_object('downloadOscarLink').pack_forget()
    else:
        self.builder.get_object('downloadOscarLink').pack(fill='both', expand=True, padx=10, pady=5, side='top')


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
