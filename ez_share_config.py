import threading
import tkinter as tk
import requests
import subprocess
from tkinter import messagebox
from wifi_utils import connect_to_wifi, wifi_connected
from utils import update_status, disable_ui_elements, enable_ui_elements

class EzShareConfig:
    def __init__(self, app):
        self.app = app

    def configure_ezshare(self, event=None):
        msg = messagebox.askokcancel('ez Share Config',
                                     "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.")
        if not msg:
            update_status(self.app, 'Configuration cancelled.', 'info')
            self.app.is_running = False
            self.app.enable_ui_elements()
            self.app.builder.get_object('cancel_button').config(default=tk.NORMAL)
            update_status(self.app, 'Ready.', 'info')
            return

        update_status(self.app, 'Connecting to ez Share Wi-Fi...', 'info')
        self._set_ezshare_params()
        disable_ui_elements(self.app.builder)
        self.app.builder.get_object('cancel_button').config(default=tk.ACTIVE)
        
        threading.Thread(target=self._connect_and_configure).start()

    def _connect_and_configure(self):
        try:
            connect_to_wifi(self.app.ezshare)
            self.app.main_window.after(self.app.ezshare.connection_delay * 1000, self._check_wifi_connection)
        except RuntimeError as e:
            self.app.main_window.after(0, lambda: update_status(self.app, f'Error: {e}', 'error'))
            self.app.main_window.after(0, self.app.enable_ui_elements)
            self.app.is_running = False

    def _set_ezshare_params(self):
        self.app.ezshare.set_params(
            path=self.app.config_manager.get_setting('Settings', 'path'),
            url=self.app.config_manager.get_setting('Settings', 'url'),
            start_time=None,
            show_progress=True,
            verbose=True,
            overwrite=False,
            keep_old=False,
            ssid=self.app.builder.get_object('ssid_entry').get(),
            psk=self.app.builder.get_object('psk_entry').get(),
            ignore=[],
            retries=3,
            connection_delay=5,
            debug=True
        )

    def _check_wifi_connection(self):
        if wifi_connected(self.app.ezshare):
            self._open_configuration_page()
        else:
            update_status(self.app, 'Failed to connect to the ez Share Wi-Fi.', 'error')
            enable_ui_elements(self.app.builder)
            self.app.is_running = False

    def _open_configuration_page(self):
        update_status(self.app, 'Connected to ez Share WiFi for configuration.', 'info')
        try:
            response = requests.get('http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356', timeout=5)
            if response.status_code == 200:
                update_status(self.app, 'HTTP server is reachable. Opening the configuration page...', 'info')
                subprocess.run(['open', 'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356'])
            else:
                update_status(self.app, f'Failed to reach the HTTP server. Status code: {response.status_code}', 'error')
                enable_ui_elements(self.app.builder)
                self.app.is_running = False
        except requests.RequestException as e:
            update_status(self.app, f'Failed to reach the HTTP server. Error: {e}', 'error')
            enable_ui_elements(self.app.builder)
            self.app.is_running = False
