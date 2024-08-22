import threading
import tkinter as tk
import requests
import subprocess
from tkinter import messagebox
from wifi_utils import connect_to_wifi
from utils import disable_ui_elements, enable_ui_elements
from status_manager import update_status
import logging

class EzShareConfig:
    def __init__(self, app):
        self.app = app
        logging.basicConfig(level=logging.DEBUG)

    def configure_ezshare(self, event=None):
        logging.debug("Configuring ezShare...")
        msg = messagebox.askokcancel('ez Share Config',
                                     "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.")
        if not msg:
            update_status(self.app, 'Configuration cancelled.', 'info')
            logging.info("Configuration cancelled by user.")
            self.app.is_running = False
            self.app.enable_ui_elements()
            self.app.builder.get_object('cancel_button').config(default=tk.NORMAL)
            update_status(self.app, 'Ready.', 'info')
            return

        update_status(self.app, 'Connecting to ez Share Wi-Fi...', 'info')
        self._set_ezshare_params()
        disable_ui_elements(self.app.builder)
        self.app.builder.get_object('cancel_button').config(default=tk.NORMAL)
        
        threading.Thread(target=self._connect_and_configure).start()

    def _connect_and_configure(self):
        try:
            logging.debug("Starting connection to Wi-Fi...")
            connect_to_wifi(self.app.ezshare, self.app.builder.get_object('ssid_entry').get(), self.app.builder.get_object('psk_entry').get())
            if self.app.is_running:  # Check if still running before proceeding
                self.app.main_window.after(self.app.ezshare.connection_delay * 1000, self._check_wifi_connection)
            else:
                logging.info("Configuration was cancelled during the connection delay.")
        except RuntimeError as e:
            logging.error(f"Error during Wi-Fi connection: {e}")
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
        logging.debug("Parameters set for ezShare.")

    def _check_wifi_connection(self):
        if self.app.ezshare.wifi_connected():
            self._open_configuration_page()
        else:
            update_status(self.app, 'Failed to connect to the ez Share Wi-Fi.', 'error')
            logging.warning("Failed to connect to Wi-Fi.")
            enable_ui_elements(self.app.builder)
            self.app.is_running = False

    def _open_configuration_page(self):
        logging.info("Connected to ez Share WiFi for configuration.")
        update_status(self.app, 'Connected to ez Share WiFi for configuration.', 'info')
        try:
            response = requests.get('http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356', timeout=5)
            if response.status_code == 200:
                update_status(self.app, 'HTTP server is reachable. Opening the configuration page...', 'info')
                subprocess.run(['open', 'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356'])
                logging.info("Configuration page opened.")
            else:
                update_status(self.app, f'Failed to reach the HTTP server. Status code: {response.status_code}', 'error')
                logging.error(f"HTTP server not reachable. Status code: {response.status_code}")
                enable_ui_elements(self.app.builder)
                self.app.is_running = False
        except requests.RequestException as e:
            update_status(self.app, f'Failed to reach the HTTP server. Error: {e}', 'error')
            logging.error(f"Failed to reach HTTP server: {e}")
            enable_ui_elements(self.app.builder)
            self.app.is_running = False
