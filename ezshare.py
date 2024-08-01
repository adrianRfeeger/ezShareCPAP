import pathlib
import logging
import requests
import time
import urllib.parse
import subprocess
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from wifi import connect_to_wifi, disconnect_from_wifi, wifi_connected
from file_ops import recursive_traversal, list_dir


class EzShare:
    """
    Class to manage file transfers from an EzShare SD card.
    """

    def __init__(self):
        self.path = None
        self.url = None
        self.start_time = None
        self.show_progress = None
        self.overwrite = None
        self.keep_old = None
        self.ssid = None
        self.psk = None
        self.previous_ssid = None
        self.previous_psk = None
        self.connection_id = None
        self.interface_name = None
        self.connected = False
        self.session = requests.Session()
        self.ignore = None
        self.retries = None
        self.retry = None
        self.connection_delay = None
        self.debug = None
        self.progress_callback = None
        self.status_callback = None
        self.total_files = 0
        self.processed_files = 0

    def set_params(self, path, url, start_time, show_progress, verbose,
                   overwrite, keep_old, ssid, psk, ignore, retries, connection_delay, debug):
        """
        Set parameters for the EzShare instance.
        """
        log_level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARN
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=log_level)
        self.path = pathlib.Path(path).expanduser()
        self.url = url
        self.start_time = start_time
        self.show_progress = show_progress
        self.overwrite = overwrite
        self.keep_old = keep_old
        self.ssid = ssid
        self.psk = psk
        self.previous_ssid = self.get_current_ssid()
        self.previous_psk = self.get_current_psk(self.previous_ssid)
        self.ignore = ['.', '..', 'back to photo'] + ignore
        self.retries = retries
        self.retry = Retry(total=retries, backoff_factor=0.25)
        self.connection_delay = connection_delay
        self.session.mount('http://', HTTPAdapter(max_retries=self.retry))

    def get_current_ssid(self):
        """
        Get the current SSID of the connected Wi-Fi network.
        """
        cmd = "networksetup -getairportnetwork en0"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.split(": ")[1].strip()
        except subprocess.CalledProcessError as e:
            self.print(f'Error getting current SSID: {e.stderr}')
            return None

    def get_current_psk(self, ssid):
        """
        Get the PSK for the specified SSID.
        """
        cmd = f"/usr/sbin/security find-generic-password -ga '{ssid}' | grep 'password:' | cut -d'\"' -f2"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.print(f'Error getting current PSK for {ssid}: {e.stderr}')
            return None

    def set_progress_callback(self, callback):
        """
        Set the callback function for progress updates.
        """
        self.progress_callback = callback

    def set_status_callback(self, callback):
        """
        Set the callback function for status updates.
        """
        self.status_callback = callback

    def update_progress(self, value):
        """
        Update the progress percentage.
        """
        if self.progress_callback:
            self.progress_callback(min(max(0, value), 100))

    def update_status(self, message):
        """
        Update the status message.
        """
        if self.status_callback:
            self.status_callback(message)

    def print(self, message):
        """
        Print the status message if progress is being shown.
        """
        if self.show_progress:
            print(message)
        self.update_status(message)

    def run(self):
        """
        Main method to start the file transfer process.
        """
        self.update_status('Starting process...')
        try:
            if self.ssid:
                self.update_status(f'Connecting to {self.ssid}...')
                self.print(f'Connecting to {self.ssid}.')
                try:
                    connect_to_wifi(self)
                    self.update_status(f'Connected to {self.ssid}.')
                except RuntimeError as e:
                    self.update_status(f'Failed to connect to {self.ssid}.')
                    logging.warning('Failed to connect to %s. Error: %s', self.ssid, str(e))
                    return

                self.print('Waiting a few seconds for connection to establish...')
                time.sleep(self.connection_delay)

            if not wifi_connected(self):
                self.update_status('Unable to connect automatically, please connect manually.')
                logging.warning('No Wi-Fi connection was established. Attempting to continue...')
                return

            self.path.mkdir(parents=True, exist_ok=True)
            self.update_status(f'Path {self.path} created.')

            self.update_status('Establishing files for download...')
            self.total_files = self.calculate_total_files(self.url, self.path, self.overwrite)
            self.update_status(f'Total files to sync: {self.total_files}')
            
            # Check for zero files to sync
            if self.total_files == 0:
                self.update_status('No files to sync. Process completed.')
                return

            self.update_status('Starting file transfer...')
            self.processed_files = recursive_traversal(self, self.url, self.path, self.total_files, self.processed_files)
            self.update_status('File transfer completed.')
        finally:
            self.disconnect_from_wifi()
            self.update_status('Disconnected from Wi-Fi.')

    def calculate_total_files(self, url, dir_path, overwrite):
        """
        Calculate the total number of files to be synced.
        """
        total_files = 0
        files, dirs = list_dir(self, url)
        for filename, _, file_ts in files:
            local_path = dir_path / filename
            if overwrite or not local_path.is_file() or local_path.stat().st_mtime < file_ts:
                total_files += 1
        for dirname, dir_url in dirs:
            new_dir_path = dir_path / dirname
            absolute_dir_url = urllib.parse.urljoin(url, dir_url)
            total_files += self.calculate_total_files(absolute_dir_url, new_dir_path, overwrite)
        return total_files

    def disconnect_from_wifi(self):
        """
        Disconnect from the Wi-Fi network.
        """
        try:
            disconnect_from_wifi(self)
        except RuntimeError as e:
            logging.error(f'Error disconnecting from Wi-Fi: {e}')
        finally:
            self.connected = False
            self.connection_id = None
