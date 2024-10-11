# ez_share_config.py
import threading
import tkinter as tk
import requests
import subprocess
from tkinter import messagebox
from wifi_utils import ConnectionManager
from utils import set_default_button_states, set_process_button_states, update_button_state
from status_manager import update_status
import logging

class EzShareConfig:
    def __init__(self, app):
        self.app = app
        self.connection_manager = ConnectionManager()
        self._is_cancelled = False  # Track whether the process has been cancelled
        self.is_connected = False  # Track whether the Wi-Fi is connected
        logging.basicConfig(level=logging.DEBUG)

    def _set_ezshare_params(self):
        """
        Set the parameters for the ezShare instance from the application's configuration settings.
        """
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
            debug=True,
        )
        logging.debug("Parameters set for ezShare.")

    def configure_ezshare(self, event=None):
        logging.debug("Configuring ezShare...")
        msg = messagebox.askokcancel(
            'ez Share Config',
            "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.",
        )
        if not msg:
            update_status(self.app, 'Configuration cancelled.', 'info')
            logging.info("Configuration cancelled by user.")
            self._cleanup()
            return

        update_status(self.app, 'Connecting to ez Share Wi-Fi...', 'info')
        self._set_ezshare_params()
        set_process_button_states(self.app)  # Disable buttons except cancel
        self.app.is_running = True

        threading.Thread(target=self._connect_and_configure).start()

    def _connect_and_configure(self):
        ssid = self.app.builder.get_object('ssid_entry').get()
        psk = self.app.builder.get_object('psk_entry').get()

        try:
            logging.debug("Starting connection to Wi-Fi...")
            self.connection_manager.connect(ssid, psk)

            if self.connection_manager.connected and not self._is_cancelled:
                self.is_connected = True
                self.app.main_window.after(
                    self.app.ezshare.connection_delay * 1000, self._check_wifi_connection
                )
            else:
                logging.info("Configuration was cancelled during the connection delay.")
                self._cleanup()

        except RuntimeError as e:
            logging.error(f"Error during Wi-Fi connection: {e}")
            self.app.main_window.after(
                0, lambda: update_status(self.app, f'Error: {e}', 'error')
            )
            self._cleanup()

    def _check_wifi_connection(self):
        if self.connection_manager.connected and not self._is_cancelled:
            self._open_configuration_page()
        else:
            update_status(self.app, 'Failed to connect to the ez Share Wi-Fi.', 'error')
            logging.warning("Failed to connect to Wi-Fi.")
            self._cleanup()

    def _open_configuration_page(self):
        logging.info("Connected to ez Share WiFi for configuration.")
        update_status(self.app, 'Connected to ez Share WiFi for configuration.', 'info')
        try:
            response = requests.get(
                'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356',
                timeout=5,
            )
            if response.status_code == 200:
                update_status(
                    self.app,
                    'HTTP server is reachable. Opening the configuration page...',
                    'info',
                )
                subprocess.run(
                    [
                        'open',
                        'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356',
                    ]
                )
                logging.info("Configuration page opened.")
            else:
                update_status(
                    self.app,
                    f'Failed to reach the HTTP server. Status code: {response.status_code}',
                    'error',
                )
                logging.error(f"HTTP server not reachable. Status code: {response.status_code}")
                self._cleanup()
        except requests.RequestException as e:
            update_status(
                self.app, f'Failed to reach the HTTP server. Error: {e}', 'error'
            )
            logging.error(f"Failed to reach HTTP server: {e}")
            self._cleanup()

    def cancel_ezshare_config(self):
        logging.info("User initiated cancellation of ez Share configuration.")
        self.app.is_running = False  # Stop the ongoing process
        self._is_cancelled = True  # Set the cancellation flag

        ssid = self.app.builder.get_object('ssid_entry').get()
        try:
            if self.connection_manager.connected:
                self.connection_manager.disconnect(ssid)
                logging.info("Wi-Fi disconnection attempted.")
                self.is_connected = False
        except Exception as e:
            logging.error(f"Error while disconnecting Wi-Fi: {e}")

        self._cleanup()

    def _cleanup(self):
        logging.info("Cleaning up after configuration.")
        self.app.is_running = False
        set_default_button_states(self.app)  # Reset buttons to default state
        update_status(self.app, 'Ready.', 'info')
        self.app.builder.get_object('progress_bar')['value'] = 0
        self._is_cancelled = False  # Reset the cancellation flag
        self.is_connected = False  # Reset the connection status
