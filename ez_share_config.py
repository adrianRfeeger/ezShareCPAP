import subprocess
import requests
import time
from tkinter import messagebox
from wifi_utils import connect_to_wifi, reconnect_to_original_wifi, wifi_connected

class EzShareConfig:
    def __init__(self, app):
        self.app = app

    def configure_ezshare(self, event=None):
        msg = messagebox.askokcancel('ez Share Config',
                                     "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.")
        if msg:
            try:
                self.app.update_status('Connecting to ez Share Wi-Fi...', 'info')
                self.app.ezshare.set_params(
                    path=self.app.config_manager.get_setting('Settings', 'path'),
                    url=self.app.config_manager.get_setting('Settings', 'url'),
                    start_time=None,
                    show_progress=True,
                    verbose=True,
                    overwrite=False,
                    keep_old=False,
                    ssid=self.app.builder.get_object('ssidEntry').get(),
                    psk=self.app.builder.get_object('pskEntry').get(),
                    ignore=[],
                    retries=3,
                    connection_delay=5,
                    debug=True
                )
                connect_to_wifi(self.app.ezshare)
                time.sleep(self.app.ezshare.connection_delay)
                if wifi_connected(self.app.ezshare):
                    self.app.update_status(f'Connected to {self.app.builder.get_object("ssidEntry").get()}.', 'info')
                    self.app.update_status('Checking if the ez Share HTTP server is reachable...', 'info')
                    try:
                        response = requests.get('http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356', timeout=5)
                        if response.status_code == 200:
                            self.app.update_status('HTTP server is reachable. Opening the configuration page...', 'info')
                            subprocess.run(['open', 'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356'])
                            messagebox.showinfo('Reconnect to Original Wi-Fi', 'Once configuration is complete click OK to reconnect to your original Wi-Fi network.')
                            self.app.update_status('Reconnecting to original Wi-Fi...', 'info')
                            success = reconnect_to_original_wifi(self.app.ezshare)
                            if success:
                                self.app.update_status('Reconnected to original Wi-Fi.', 'info')
                            else:
                                self.app.update_status('Failed to reconnect to original Wi-Fi. Please do so manually.', 'error')
                            self.app.callbacks.cancel_process()  # Call cancel_process after configuration
                        else:
                            self.app.update_status(f'Failed to reach the HTTP server. Status code: {response.status_code}', 'error')
                    except requests.RequestException as e:
                        self.app.update_status(f'Failed to reach the HTTP server. Error: {e}', 'error')
                else:
                    self.app.update_status('Failed to connect to the ez Share Wi-Fi.', 'error')
            except RuntimeError as e:
                self.app.update_status(f'Error: {e}', 'error')
        else:
            self.app.update_status('Configuration cancelled.', 'info')
