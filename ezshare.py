import pathlib
import logging
import requests
import urllib
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from wifi_utils import connect_to_wifi, disconnect_from_wifi, wifi_connected
from file_ops import recursive_traversal, list_dir

class ezShare:
    def __init__(self):
        self.path = None
        self.url = None
        self.start_time = None
        self.show_progress = None
        self.overwrite = None
        self.keep_old = None
        self.ssid = None
        self.psk = None
        self.connection_id = None
        self.interface_name = None
        self.connected = False
        self.session = requests.Session()
        self.ignore = ['.', '..', 'back to photo']
        self.retries = None
        self.connection_delay = None
        self.debug = None
        self.progress_callback = None
        self.status_callback = None
        self.total_files = 0
        self.processed_files = 0
        self._is_running = True
        self._configure_logging()
        self.retry_policy = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=self.retry_policy))

    def _configure_logging(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    def set_params(self, path, url, start_time, show_progress, verbose,
                   overwrite, keep_old, ssid, psk, ignore, retries, connection_delay, debug):
        log_level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARN
        logging.getLogger().setLevel(log_level)
        self.path = pathlib.Path(path).expanduser()
        self.url = url
        self.start_time = start_time
        self.show_progress = show_progress
        self.overwrite = overwrite
        self.keep_old = keep_old
        self.ssid = ssid
        self.psk = psk
        self.ignore = ['.', '..', 'back to photo'] + ignore
        self.retries = retries
        self.connection_delay = connection_delay
        self.debug = debug

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def set_status_callback(self, callback):
        self.status_callback = callback

    def update_progress(self, value):
        if self.progress_callback:
            self.progress_callback(min(max(0, value), 100))

    def update_status(self, message, message_type='info'):
        if self.status_callback:
            self.status_callback(message, message_type)

    def print(self, message):
        if self.show_progress:
            print(message)
        self.update_status(message)

    def run(self, after_callback=None):
        self.update_status('Starting process...')
        if self.ssid:
            self.update_status(f'Connecting to {self.ssid}...')
            try:
                connect_to_wifi(self, self.ssid, self.psk)  # Pass ssid and psk
                self.update_status(f'Connected to {self.ssid}.')
                if not self._is_running:
                    raise RuntimeError("Operation cancelled by user.")
            except RuntimeError as e:
                self.update_status(f'Failed to connect to {self.ssid}.', 'error')
                return

            self.run_after_connection_delay()

        disconnect_from_wifi(self)
        self.update_status('Disconnected from Wi-Fi.')

    def calculate_total_files(self, url, dir_path, overwrite):
        total_files = 0
        files, dirs = list_dir(self, url)
        for filename, file_url, file_ts in files:
            local_path = dir_path / filename
            if overwrite or not local_path.is_file() or local_path.stat().st_mtime < file_ts:
                total_files += 1
        for dirname, dir_url in dirs:
            new_dir_path = dir_path / dirname
            absolute_dir_url = urllib.parse.urljoin(url, dir_url)
            total_files += self.calculate_total_files(absolute_dir_url, new_dir_path, overwrite)
        return total_files

    def run_after_connection_delay(self):
        if not wifi_connected(self):
            self.update_status('Unable to connect automatically, please connect manually.', 'error')
            return

        self.path.mkdir(parents=True, exist_ok=True)
        self.update_status(f'Path {self.path} created.')
        self.update_status('Establishing files for download...')
        self.total_files = self.calculate_total_files(self.url, self.path, self.overwrite)
        self.update_status(f'Total files to sync: {self.total_files}')
        if self.total_files == 0:
            self.update_status('No files to sync. Process completed.')
            return

        self.processed_files = recursive_traversal(self, self.url, self.path, self.total_files, self.processed_files, lambda: self._is_running)
        self.update_status('File transfer completed.')

    def stop(self):
        self._is_running = False
        self.update_status('Process stopped by user.', 'info')
