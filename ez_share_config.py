import subprocess
import requests
import time
from tkinter import messagebox
from wifi import connect_to_wifi, reconnect_to_original_wifi, wifi_connected

def ez_share_config(app, event=None):
    msg = messagebox.askokcancel('ez Share Config',
                                 "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK. P.S. the default password is 'admin'.")
    if msg:
        try:
            app.update_status('Connecting to ez Share Wi-Fi...', 'info')
            app.ezshare.set_params(
                path=app.config['Settings']['path'],
                url=app.config['Settings']['url'],
                start_time=None,
                show_progress=True,
                verbose=True,
                overwrite=False,
                keep_old=False,
                ssid=app.builder.get_object('ssidEntry').get(),
                psk=app.builder.get_object('pskEntry').get(),
                ignore=[],
                retries=3,
                connection_delay=5,  # Ensure connection_delay is set
                debug=True
            )
            connect_to_wifi(app.ezshare)
            time.sleep(app.ezshare.connection_delay)
            if wifi_connected(app.ezshare):
                app.update_status(f'Connected to {app.builder.get_object("ssidEntry").get()}.', 'info')
                app.update_status('Checking if the ez Share HTTP server is reachable...', 'info')
                try:
                    response = requests.get('http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356', timeout=5)
                    if response.status_code == 200:
                        app.update_status('HTTP server is reachable. Opening the configuration page...', 'info')
                        subprocess.run(['open', 'http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356'])
                        messagebox.showinfo('Reconnect to Original Wi-Fi', 'Once configuration is complete click OK to reconnect to your original Wi-Fi network.')
                        app.update_status('Reconnecting to original Wi-Fi...', 'info')
                        success = reconnect_to_original_wifi(app.ezshare)
                        if success:
                            app.update_status('Reconnected to original Wi-Fi.', 'info')
                        else:
                            app.update_status('Failed to reconnect to original Wi-Fi. Please do so manually.', 'error')
                        app.cancel_process()  # Call cancel_process after configuration
                    else:
                        app.update_status(f'Failed to reach the HTTP server. Status code: {response.status_code}', 'error')
                except requests.RequestException as e:
                    app.update_status(f'Failed to reach the HTTP server. Error: {e}', 'error')
            else:
                app.update_status('Failed to connect to the ez Share Wi-Fi.', 'error')
        except RuntimeError as e:
            app.update_status(f'Error: {e}', 'error')
    else:
        app.update_status('Configuration cancelled.', 'info')
