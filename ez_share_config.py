# ez_share_config.py
import threading
import tkinter as tk
import requests
import subprocess
from tkinter import messagebox
from wifi_utils import WiFiManager, VerifySpec
from utils import set_default_button_states, set_process_button_states, update_button_state
from status_manager import update_status
import logging


class EzShareConfig:
    def __init__(self, app):
        self.app = app
        self.wifi = WiFiManager()  # swapped ConnectionManager -> WiFiManager
        self._is_cancelled = False  # Track whether the process has been cancelled
        self.is_connected = False   # Track whether the Wi‑Fi is connected
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
            "To configure the ez Share SD card, the settings page will be opened with your default browser. "
            "Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. "
            "P.S. the default password is 'admin'.",
        )
        if not msg:
            update_status(self.app, 'Configuration cancelled.', 'info')
            logging.info("Configuration cancelled by user.")
            self._cleanup()
            return

        update_status(self.app, 'Connecting to ez Share Wi‑Fi...', 'info')
        self._set_ezshare_params()
        set_process_button_states(self.app)  # Disable buttons except cancel
        self.app.is_running = True

        threading.Thread(target=self._connect_and_configure, name="EzShareConfigThread", daemon=True).start()

    def _connect_and_configure(self):
        ssid = self.app.builder.get_object('ssid_entry').get()
        psk = self.app.builder.get_object('psk_entry').get()

        try:
            logging.debug("Starting connection to Wi‑Fi...")
            # Strong verification spec: SSID + expected subnet + ping gateway
            spec = VerifySpec(
                expected_ssid=ssid,
                expected_subnet_prefix="192.168.4.",
                gateway_ip="192.168.4.1",
            )

            ok = self.wifi.ensure_connected(ssid, psk, verify=spec)
            if not ok or self._is_cancelled:
                raise RuntimeError("Failed to connect/verify Wi‑Fi or process was canceled.")

            self.is_connected = True
            self.app.main_window.after(0, lambda: update_status(self.app, 'Connected to ez Share Wi‑Fi for configuration.', 'info'))

            # Optional: keep the connection verified while the page is open
            # self.wifi.start_monitor(ssid, psk, verify=spec)

            # After we are verified online with the card, open the config page
            self._open_configuration_page()

        except RuntimeError as e:
            logging.error(f"Error during Wi‑Fi connection: {e}")
            self.app.main_window.after(0, lambda: update_status(self.app, f'Error: {e}', 'error'))
            self._cleanup()
        except Exception as e:
            logging.exception("Unexpected error during configuration.")
            self.app.main_window.after(0, lambda: update_status(self.app, f'Unexpected error: {e}', 'error'))
            self._cleanup()
        finally:
            # We intentionally keep Wi‑Fi up until after attempting to open the page.
            pass

    def _open_configuration_page(self):
        logging.info("Opening ez Share configuration page.")
        try:
            url = 'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356'
            # Quick reachability check with short timeout
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                self.app.main_window.after(0, lambda: update_status(
                    self.app, 'HTTP server is reachable. Opening the configuration page...', 'info'
                ))
                # macOS 'open' is used in the original; keep behavior consistent.
                subprocess.run(['open', url])
                logging.info("Configuration page opened.")
            else:
                self.app.main_window.after(0, lambda: update_status(
                    self.app, f'Failed to reach the HTTP server. Status code: {response.status_code}', 'error'
                ))
                logging.error(f"HTTP server not reachable. Status code: {response.status_code}")
        except requests.RequestException as e:
            self.app.main_window.after(0, lambda: update_status(
                self.app, f'Failed to reach the HTTP server. Error: {e}', 'error'
            ))
            logging.error(f"Failed to reach HTTP server: {e}")
        finally:
            # Disconnect after attempting to open the page; also forget EzShare and restore previous network
            try:
                if self.wifi.connected:
                    ssid = self.app.builder.get_object('ssid_entry').get()
                    prev = getattr(self.wifi, '_prev_ssid', None)
                    self.wifi.disconnect_forget_and_restore(ssid, restore_previous=True)
                    self.is_connected = False
                    restored = prev if prev and prev != ssid else None
                    logging.info("Wi‑Fi disconnected and EzShare removed from Preferred Networks.")
                    self.app.main_window.after(0, lambda: update_status(
                        self.app,
                        'Disconnected and removed EzShare from Preferred Networks.',
                        'info',
                        restored_ssid=restored,
                    ))
            except Exception as e:
                logging.error(f"Error while disconnecting Wi‑Fi: {e}")
                self.app.main_window.after(0, lambda: update_status(self.app, f'Wi‑Fi cleanup issue: {e}', 'error'))

            self._cleanup()

    def cancel_ezshare_config(self):
        logging.info("User initiated cancellation of ez Share configuration.")
        self.app.is_running = False
        self._is_cancelled = True

        try:
            if self.wifi.connected:
                ssid = self.app.builder.get_object('ssid_entry').get()
                prev = getattr(self.wifi, '_prev_ssid', None)
                self.wifi.disconnect_forget_and_restore(ssid, restore_previous=True)
                restored = prev if prev and prev != ssid else None
                logging.info("Wi‑Fi disconnection + forget attempted.")
                self.app.main_window.after(0, lambda: update_status(
                    self.app,
                    'Disconnected and removed EzShare from Preferred Networks.',
                    'info',
                    restored_ssid=restored,
                ))
                self.is_connected = False
        except Exception as e:
            logging.error(f"Error while disconnecting Wi‑Fi: {e}")
            self.app.main_window.after(0, lambda: update_status(self.app, f'Wi‑Fi cleanup issue: {e}', 'error'))

        self._cleanup()

    def _cleanup(self):
        logging.info("Cleaning up after configuration.")
        self.app.is_running = False
        set_default_button_states(self.app)  # Reset buttons to default state
        update_status(self.app, 'Ready.', 'info')
        self.app.builder.get_object('progress_bar')['value'] = 0
        self._is_cancelled = False  # Reset the cancellation flag
        self.is_connected = False   # Reset the connection status
