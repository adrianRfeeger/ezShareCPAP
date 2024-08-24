import webbrowser
import logging
import time
from tkinter import messagebox
from wifi_utils import connect_to_wifi, disconnect_wifi, reset_wifi_configuration
from status_manager import update_status
from utils import set_process_button_states, set_default_button_states

class EzShareConfig:
    def __init__(self, app):
        self.app = app
        self.connected_interface = None

    def configure_ezshare(self):
        # Confirm with the user before proceeding
        if not messagebox.askokcancel(
            "Configure ez Share",
            "To configure the ez Share SD card, the settings page will be opened with your default browser. Ensure that you update the settings in ezShareCPAP with any changes that you make to the SSID or PSK.\n\nP.S. the default password is 'admin'."
        ):
            logging.info("Configuration cancelled by user.")
            return

        # Retrieve SSID and PSK from the UI
        ssid = self.app.builder.get_object('ssid_entry').get()
        psk = self.app.builder.get_object('psk_entry').get()

        logging.debug(f"SSID retrieved: {ssid}")
        logging.debug(f"PSK retrieved: {psk}")

        if not ssid or not psk:
            logging.error("SSID or PSK is missing. Cannot connect to Wi-Fi.")
            update_status(self.app, "SSID or PSK is missing.", "error")
            return

        # Update the UI to reflect that a process is running
        set_process_button_states(self.app)
        self.app.is_running = True

        update_status(self.app, "Connecting to ez Share Wi-Fi...", "info")

        try:
            # Attempt to connect to the Wi-Fi network
            self.connected_interface = connect_to_wifi(ssid, psk)
            logging.info(f"Interface Name Set: {self.connected_interface}")
            update_status(self.app, "Connected to ez Share WiFi for configuration.", "info")

            # Attempt to open the configuration page
            config_url = "http://192.168.4.1/publicdir/index.htm?vtype=0&fdir=&ftype=1&devw=320&devh=356"
            for attempt in range(3):
                try:
                    logging.info(f"Attempt {attempt + 1} to open the configuration page...")
                    webbrowser.open(config_url)
                    update_status(self.app, "HTTP server is reachable. Opening the configuration page...", "info")
                    break
                except Exception as e:
                    logging.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == 2:
                        update_status(self.app, f"Failed to reach the configuration page: {e}", "error")
                        raise e

        except Exception as e:
            logging.error(f"Error during configuration: {str(e)}")
            update_status(self.app, f"Error: {str(e)}", "error")
            self.cancel_ezshare_config()

        def cancel_ezshare_config(self):
            logging.info("Attempting to cancel ez Share configuration.")
            
            # Check if there's an ongoing process
            if not self.app.is_running:
                logging.info("No ongoing process to cancel.")
                return

            try:
                # Stop the worker thread if it's running
                if self.app.worker and self.app.worker.is_alive():
                    logging.info("Stopping running worker thread.")
                    self.app.worker.stop()
                    self.app.worker.join()  # Ensure the worker thread has fully terminated
                    logging.info("Worker thread stopped successfully.")

                # Disconnect from Wi-Fi if connected
                if self.connected_interface:
                    logging.info(f"Disconnecting from Wi-Fi SSID={self.app.builder.get_object('ssid_entry').get()} on interface={self.connected_interface}")
                    disconnect_wifi(self.app.builder.get_object('ssid_entry').get(), self.connected_interface)
                    reset_wifi_configuration(self.connected_interface)
                    logging.info("Wi-Fi configuration reset successfully.")
                    self.connected_interface = None
                else:
                    logging.info("No active Wi-Fi connection to disconnect, or process was canceled before connection.")

                # Reset the UI and internal states
                self.app.is_running = False
                set_default_button_states(self.app)
                self.app.builder.get_object('progress_bar')['value'] = 0
                logging.info("Process cancelled and UI reset. Ready for new operations.")
                update_status(self.app, "Configuration cancelled.", "info")

            except Exception as e:
                logging.error(f"Error during process cancellation: {str(e)}")
                update_status(self.app, f"Cancellation error: {str(e)}", "error")
