# worker.py
import threading
import logging

class EzShareWorker(threading.Thread):
    def __init__(self, ezshare, queue, name="EzShareWorkerThread", app=None):
        super().__init__(name=name)
        self.ezshare = ezshare
        self.queue = queue
        self.app = app
        self._is_running = True

    def run(self):
        logging.info(f"{self.name} started.")
        success = False
        try:
            self.ezshare.set_progress_callback(self.update_progress)
            self.ezshare.set_status_callback(self.update_status)
            success = bool(self.ezshare.run())
        except Exception as e:
            logging.error(f"{self.name} encountered an error: {str(e)}")
            self.update_status(f'Error: {e}', 'error')
        finally:
            self._cleanup(success)

    def update_progress(self, value):
        logging.debug(f"{self.name} updating progress: {value}")
        if value == 'no_files':
            self.queue.put(('no_files',))
        else:
            self.queue.put(('progress', min(max(0, value), 100)))

    def update_status(self, message, message_type='info'):
        logging.debug(f"{self.name} updating status: {message} (type: {message_type})")
        if self.app:
            self.queue.put(('status', message, message_type))
        else:
            logging.error("Cannot update status: app object is None.")

    def stop(self):
        logging.info(f"{self.name} stop requested.")
        self._is_running = False
        self.ezshare.stop()
        self.queue.put(('stop',))

    def _cleanup(self, success=False):
        logging.info(f"Cleaning up {self.name}.")
        if self.ezshare.connected:
            if self.ezshare.connection_manager.disconnect(self.ezshare.ssid):
                self.ezshare.connected = False
            else:
                self.update_status('Could not disconnect from Wi-Fi automatically.', 'error')
        self.queue.put(('finished', success))
        logging.info(f"{self.name} cleanup completed.")
