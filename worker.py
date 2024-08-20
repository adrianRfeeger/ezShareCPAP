import threading
import logging
from wifi_utils import disconnect_wifi

class EzShareWorker(threading.Thread):
    def __init__(self, ezshare, queue, name="EzShareWorkerThread"):
        super().__init__(name=name)
        self.ezshare = ezshare
        self.queue = queue
        self._is_running = True
        self.interface = None  # Add an attribute to store the interface

    def run(self):
        logging.info(f"{self.name} started.")
        try:
            self.ezshare.set_progress_callback(self.update_progress)
            self.ezshare.set_status_callback(self.update_status)
            self.interface = self.ezshare.run()  # Capture the interface used during connection
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
        self.queue.put(('status', message, message_type))

    def stop(self):
        logging.info(f"{self.name} stop requested.")
        self._is_running = False
        self.ezshare.stop()
        self.queue.put(('stop',))

    def _cleanup(self):
        logging.info(f"Cleaning up {self.name}.")
        if self.ezshare.connected:
            disconnect_wifi(self.ezshare.ssid, self.interface)  # Use the stored interface for disconnection
        self.queue.put(('finished',))
        logging.info(f"{self.name} cleanup completed.")
