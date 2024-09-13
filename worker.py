# worker.py
import threading
import logging
from wifi_utils import disconnect_wifi

class EzShareWorker(threading.Thread):
    def __init__(self, ezshare, queue, name="EzShareWorkerThread", app=None):
        super().__init__(name=name)
        self.ezshare = ezshare
        self.queue = queue
        self.app = app  # Ensure the app object is correctly passed and stored
        self._is_running = True
        self.interface = None

    def run(self):
        logging.info(f"{self.name} started.")
        try:
            self.ezshare.set_progress_callback(self.update_progress)
            self.ezshare.set_status_callback(self.update_status)
            self.interface = self.ezshare.run()
        except Exception as e:
            logging.error(f"{self.name} encountered an error: {str(e)}")
            self.update_status(f'Error: {e}', 'error')
        finally:
            self._cleanup()

    def update_progress(self, value):
        logging.debug(f"{self.name} updating progress: {value}%")
        self.queue.put(('progress', min(max(0, value), 100)))

    def update_status(self, message, message_type='info'):
        logging.debug(f"{self.name} updating status: {message} (type: {message_type})")
        if self.app:  # Ensure app is not None
            self.queue.put(('status', message, message_type))
        else:
            logging.error("Cannot update status: app object is None.")

    def stop(self):
        logging.info(f"{self.name} stop requested.")
        self._is_running = False
        self.ezshare.stop()
        self.queue.put(('stop',))

    def _cleanup(self):
        logging.info(f"Cleaning up {self.name}.")
        if self.ezshare.connected:
            disconnect_wifi(self.ezshare.ssid, self.interface)
        self.queue.put(('finished',))
        logging.info(f"{self.name} cleanup completed.")
