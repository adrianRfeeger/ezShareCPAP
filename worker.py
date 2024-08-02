# worker.py
import threading
from wifi_utils import connect_to_wifi, disconnect_from_wifi

class EzShareWorker(threading.Thread):
    def __init__(self, ezshare, queue):
        super().__init__()
        self.ezshare = ezshare
        self.queue = queue
        self._is_running = True

    def run(self):
        self.ezshare.set_progress_callback(self.update_progress)
        self.ezshare.set_status_callback(self.update_status)
        try:
            connect_to_wifi(self.ezshare)
            self.ezshare.run()
        except RuntimeError as e:
            self.update_status(f'Error: {e}', 'error')
        finally:
            self._cleanup()

    def update_progress(self, value):
        self.queue.put(('progress', min(max(0, value), 100)))

    def update_status(self, message, message_type='info'):
        self.queue.put(('status', message, message_type))

    def stop(self):
        self._is_running = False
        self.queue.put(('stop',))
        self._cleanup()

    def _cleanup(self):
        if self.ezshare.connected:
            disconnect_from_wifi(self.ezshare)
        self.queue.put(('finished',))
