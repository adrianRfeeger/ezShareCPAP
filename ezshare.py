# ezshare.py
import pathlib
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from wifi_utils import ConnectionManager
from file_ops import recursive_traversal, list_dir
import urllib.parse
import time

class ezShare:
    def __init__(self):
        self.reset_state()

    def reset_state(self):
        self.path = None
        self.url = None
        self.start_time = None
        self.show_progress = None
        self.overwrite = None
        self.keep_old = None
        self.ssid = None
        self.psk = None
        self.connected = False
        self.session = None
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
        self.connection_manager = ConnectionManager()

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
            self.update_status(f'Progress: {value:.2f}%')

    def update_status(self, message, message_type='info'):
        if self.status_callback:
            self.status_callback(message, message_type)

    def print(self, message):
        if self.show_progress:
            print(message)
        self.update_status(message)

    def run(self):
        self.update_status('Starting process...')
        if self.ssid:
            self.update_status(f'Connecting to {self.ssid}...')
            retries = self.retries
            while retries > 0 and self._is_running:
                try:
                    target_host = urllib.parse.urlparse(self.url).hostname or "192.168.4.1"
                    self.connection_manager.connect(self.ssid, self.psk, target_host=target_host)
                    if not self.connection_manager.connected or not self._is_running:
                        raise RuntimeError("Failed to connect to Wi-Fi or process was canceled.")

                    # Add a short delay before verification to allow the network to settle
                    time.sleep(2)  
                    if not self.connection_manager.verify_connection():
                        raise RuntimeError("Failed to verify Wi-Fi connection.")

                    self.update_status(f'Connected to {self.ssid}.')
                    self.connected = True
                    self.session = requests.Session()
                    self.session.mount('http://', HTTPAdapter(max_retries=self.retry_policy))
                    break  # Exit the retry loop on successful connection
                except RuntimeError as e:
                    retries -= 1
                    self.update_status(f'Connection attempt failed: {e}. Retries left: {retries}', 'error')
                    if retries == 0 or not self._is_running:
                        # If no retries left or the process was canceled, stop here.
                        self.connected = False
                        return False
                    else:
                        time.sleep(self.connection_delay)  # Wait before retrying

            # If after all attempts not connected, just return
            if not self.connected:
                return False

            # Successfully connected and verified - proceed
            success = self.run_after_connection_delay()

            # Disconnect after finishing
            if self.connected:
                self.connection_manager.disconnect(self.ssid)
                self.update_status('Disconnected from Wi-Fi.')
                self.connected = False
            return success

        else:
            self.update_status('No SSID provided, cannot connect to Wi-Fi.', 'error')
            return False

    def calculate_total_files(self, url, dir_path, overwrite):
        files, dirs = list_dir(self, url)
        if files is None and dirs is None:
            return None
        return self.calculate_total_files_from_listing(files, dirs, url, dir_path, overwrite)

    def calculate_total_files_from_listing(self, files, dirs, url, dir_path, overwrite):
        total_files = 0
        for filename, file_url, file_ts in files:
            local_path = dir_path / filename
            if overwrite or not local_path.is_file() or local_path.stat().st_mtime < file_ts:
                total_files += 1
        for dirname, dir_url in dirs:
            new_dir_path = dir_path / dirname
            absolute_dir_url = urllib.parse.urljoin(url, dir_url)
            nested_total = self.calculate_total_files(absolute_dir_url, new_dir_path, overwrite)
            if nested_total is None:
                return None
            total_files += nested_total
        return total_files

    def wait_for_directory_listing(self):
        attempts = max(1, self.retries or 1)
        delay = max(1, self.connection_delay or 1)

        for attempt in range(1, attempts + 1):
            files, dirs = list_dir(self, self.url)
            if files is not None or dirs is not None:
                return files, dirs

            if attempt < attempts and self._is_running:
                self.update_status(
                    f'Waiting for ez Share web server... attempt {attempt}/{attempts}',
                    'info'
                )
                time.sleep(delay)

        return None, None

    def run_after_connection_delay(self):
        if not self.connected or not self._is_running:
            self.update_status('Not connected. Aborting file scanning.', 'error')
            return False

        if self.path is None:
            self.update_status('Error: Path is not set.', 'error')
            return False

        self.path.mkdir(parents=True, exist_ok=True)
        self.update_status(f'Using path: {self.path}')
        self.update_status('Scanning for files to download...')

        # Test directory listing to ensure we're truly connected
        test_files, test_dirs = self.wait_for_directory_listing()
        if test_files is None and test_dirs is None:
            # If an error occurred, treat this as a connection problem
            self.update_status('Unable to retrieve directory listing. Connection issue suspected.', 'error')
            return False
        elif not test_files and not test_dirs:
            # If we got an empty listing (and no error), it may mean no files or a connection glitch.
            # Log a warning and proceed cautiously - but this at least differentiates a verified empty result.
            self.update_status('Directory listing is empty. Possibly no files or still an issue.', 'info')

        self.total_files = self.calculate_total_files_from_listing(
            test_files,
            test_dirs,
            self.url,
            self.path,
            self.overwrite
        )
        if self.total_files is None:
            self.update_status('Unable to count files because the ez Share directory could not be reached.', 'error')
            return
        self.update_status(f'Total files to sync: {self.total_files}')

        if self.total_files == 0:
            self.update_status('All files are up to date. No files to sync. Process completed.')
            if self.progress_callback:
                self.progress_callback('no_files')
            return True

        self.processed_files = recursive_traversal(
            self, self.url, self.path, self.total_files, self.processed_files, lambda: self._is_running
        )
        if self.processed_files == self.total_files:
            self.update_status('File transfer completed successfully.')
            return True
        else:
            self.update_status('File transfer incomplete.', 'error')
            return False

    def stop(self):
        self._is_running = False
        self.update_status('Process stopped by user.', 'info')
        if self.connected:
            self.connection_manager.disconnect(self.ssid)
            self.connected = False
