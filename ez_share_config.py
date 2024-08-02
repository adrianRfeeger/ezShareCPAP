# ez_share_config.py
import subprocess
import requests
from tkinter import messagebox
from wifi_utils import connect_to_wifi, disconnect_from_wifi, wifi_connected
from utils import update_status

class EzShareConfig:
    def __init__(self, app):
        self.app = app

    def configure_ezshare(self, event=None):
        msg = messagebox.askokcancel('ez Share Config',
                                     "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.")
        if not msg:
            update_status(self.app, 'Configuration cancelled.', 'info')
            return

        try:
            update_status(self.app, 'Connecting to ez Share Wi-Fi...', 'info')
            self._set_ezshare_params()
            connect_to_wifi(self.app.ezshare)
            self.app.main_window.after(self.app.ezshare.connection_delay * 1000, self._check_wifi_connection)
        except RuntimeError as e:
            update_status(self.app, f'Error: {e}', 'error')

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

    def _open_configuration_page(self):
        update_status(self.app, f'Connected to {self.app.builder.get_object("ssid_entry").get()}.', 'info')
        update_status(self.app, 'Checking if the ez Share HTTP server is reachable...', 'info')
        try:
            response = requests.get('http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356', timeout=5)
            if response.status_code == 200:
                update_status(self.app, 'HTTP server is reachable. Opening the configuration page...', 'info')
                subprocess.run(['open', 'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356'])
                messagebox.showinfo('Reconnect to Original Wi-Fi', 'Once configuration is complete click OK to disconnect from the ez Share card Wifi and reconnect to your original WiFi network.')
                update_status(self.app, 'Reconnecting to original Wi-Fi...', 'info')
                disconnect_from_wifi(self.app.ezshare)
                update_status(self.app, 'Reconnected to original Wi-Fi.', 'info')
                self.app.callbacks.cancel_process()
            else:
                update_status(self.app, f'Failed to reach the HTTP server. Status code: {response.status_code}', 'error')
        except requests.RequestException as e:
            update_status(self.app, f'Failed to reach the HTTP server. Error: {e}', 'error')
