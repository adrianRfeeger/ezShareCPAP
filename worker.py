import threading
from wifi import connect_to_wifi, disconnect_from_wifi

class EzShareWorker(threading.Thread):
    def __init__(self, ezshare, queue):
        super().__init__()
        self.ezshare = ezshare
        self.queue = queue
        self._is_running = True

    def run(self):
        """
        Run the worker thread to perform the file transfer.
        """
        self.ezshare.set_progress_callback(self.update_progress)
        self.ezshare.set_status_callback(self.update_status)
        try:
            connect_to_wifi(self.ezshare)
            self.ezshare.run()
        except RuntimeError as e:
            self.update_status(f'Error: {e}', 'error')
        finally:
            disconnect_from_wifi(self.ezshare)
            self.queue.put(('finished',))

    def update_progress(self, value):
        """
        Update the progress value in the queue.
        """
        self.queue.put(('progress', min(max(0, value), 100)))

    def update_status(self, message, message_type='info'):
        """
        Update the status message in the queue.
        """
        self.queue.put(('status', message, message_type))

    def stop(self):
        """
        Stop the worker thread.
        """
        self._is_running = False
        self.queue.put(('stop',))
        disconnect_from_wifi(self.ezshare)
