# main.py
import sys


APP_VERSION = "0.3.0"

ENTRYPOINT_HELP = (
    "Usage:\n"
    "  python main.py                 Launch the GUI\n"
    "  python main.py gui             Launch the GUI\n"
    "  python main.py sync [options]  Run from the command line\n"
    "  python main.py --cli [options] Run from the command line\n\n"
    "Use `python main.py sync --help` for CLI sync options."
)


def _direct_cli_exit(argv):
    if argv and argv[0] == 'sync':
        from cli import run_cli
        raise SystemExit(run_cli(argv[1:]))

    if argv and argv[0] == '--cli':
        from cli import run_cli
        raise SystemExit(run_cli(argv[1:]))

    if argv and argv[0] in ('-h', '--help'):
        print(ENTRYPOINT_HELP)
        raise SystemExit(0)


if __name__ == "__main__":
    _direct_cli_exit(sys.argv[1:])

import tkinter as tk
import queue
import logging
import pygubu
import platform
from tkinter import BooleanVar, messagebox
from ezshare import ezShare
from config_manager import ConfigManager, get_default_config_file
from callbacks import Callbacks
from ez_share_config import EzShareConfig
from status_manager import update_status
from utils import ensure_and_check_disk_access, resource_path, initialize_button_states, set_default_button_states, set_process_button_states, get_button_state, get_oscar_version
from worker import EzShareWorker

class EzShareCPAPUI:
    def __init__(self, master=None):
        # Initialize button states
        initialize_button_states(self)

        # Other initializations
        self.config_file = self._get_config_file()
        self.config_manager = ConfigManager(self.config_file)
        self.ezshare = ezShare()
        self.worker = None
        self.worker_queue = queue.Queue()
        self.is_running = False
        self.status_timer = None

        self.builder = pygubu.Builder()
        self.builder.add_from_file(resource_path('ezShareCPAP.ui'))
        self.main_window = self.builder.get_object('main_window', master)
        self.builder.connect_callbacks(self)

        icon_path = resource_path('icon.png')
        self.main_window.iconphoto(False, tk.PhotoImage(file=icon_path))

        self.quit_var = BooleanVar()
        self.import_oscar_var = BooleanVar()

        self.builder.get_object('quit_checkbox').config(variable=self.quit_var)
        self.builder.get_object('import_oscar_checkbox').config(variable=self.import_oscar_var)

        # Set default button states after initializing the button state dictionary
        set_default_button_states(self)

        self.callbacks = Callbacks(self)
        self.ezshare_config = EzShareConfig(self)

        # Configure buttons with their commands
        self.builder.get_object('start_button').config(command=lambda: self.handle_button_click('start_button', self.callbacks.start_process))
        self.builder.get_object('cancel_button').config(command=lambda: self.handle_button_click('cancel_button', self.callbacks.cancel_process))
        self.builder.get_object('quit_button').config(command=lambda: self.handle_button_click('quit_button', self.callbacks.quit_application))
        self.builder.get_object('save_button').config(command=lambda: self.handle_button_click('save_button', self.callbacks.save_config))
        self.builder.get_object('restore_defaults_button').config(command=lambda: self.handle_button_click('restore_defaults_button', self.callbacks.restore_defaults))
        self.builder.get_object('select_folder_button').config(command=lambda: self.handle_button_click('select_folder_button', self.callbacks.open_folder_selector))
        self.builder.get_object('configure_wifi_button').config(command=lambda: self.handle_button_click('configure_wifi_button', self.ezshare_config.configure_ezshare))

        # Bind the label (not a button) with an event
        self.builder.get_object('download_oscar_link').bind("<Button-1>", self.callbacks.open_oscar_download_page)

        self.load_config()
        self.callbacks.update_ui_checkboxes()
        ensure_and_check_disk_access(self.config_manager.get_setting('Settings', 'path'))

        logging.basicConfig(filename='application.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

        # Add Help menu
        menubar = tk.Menu(self.main_window)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.show_about_dialog)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.main_window.config(menu=menubar)

    def _get_config_file(self):
        return get_default_config_file()

    def show_about_dialog(self):
        oscar_version = get_oscar_version()
        oscar_info = f"OSCAR: {oscar_version}" if oscar_version else "OSCAR: Not installed"
        os_name = platform.system()
        
        about_message = (
            "ezShareCPAP\n"
            f"Version {APP_VERSION}\n"
            "Cross-Platform (macOS, Windows, Linux)\n"
            "Compatible with OSCAR 1.x and OSCAR 2.0.0+\n"
            "\n"
            "This application downloads CPAP data from an ez Share Wi-Fi SD card "
            "and imports it into OSCAR.\n"
            "\n"
            f"Platform: {os_name}\n"
            f"{oscar_info}"
        )
        messagebox.showinfo("About ezShareCPAP", about_message)

    def handle_button_click(self, button_name, action):
        if get_button_state(self, button_name)['enabled']:
            action()
        else:
            logging.info(f"Button '{button_name}' is disabled and was clicked.")

    def enable_ui_elements(self):
        set_default_button_states(self)

    def disable_ui_elements(self):
        set_process_button_states(self)

    def update_status(self, message, message_type='info'):
        logging.debug(f"Attempting to update status to '{message}' with type '{message_type}'")
        update_status(self, message, message_type)

    def reset_status(self):
        logging.debug(f"Checking if status should be reset to 'Ready.' (is_running={self.is_running})")
        if not self.is_running:
            logging.info("Resetting status to 'Ready.'")
            self.update_status('Ready.', 'info')

    def process_worker_queue(self):
        try:
            msg = self.worker_queue.get_nowait()
            if msg[0] == 'progress':
                self.builder.get_object('progress_bar')['value'] = msg[1]
            elif msg[0] == 'status':
                self.update_status(msg[1], msg[2])
            elif msg[0] == 'no_files':
                self.handle_no_files()
            elif msg[0] == 'finished':
                success = msg[1]
                self.process_finished(success)
        except queue.Empty:
            pass  # No message to process, continue normally

        if self.is_running:
            self.main_window.after(100, self.process_worker_queue)

    def process_finished(self, success=True):
        logging.info("Process finished")
        self.is_running = False
        set_default_button_states(self)
        self.builder.get_object('progress_bar')['value'] = 0

        if success:
            self.update_status('Process completed successfully.', 'info')
            # Trigger completion tasks based on user preferences
            if self.quit_var.get() or self.import_oscar_var.get():
                self.prompt_completion_tasks()
        else:
            self.update_status('Process failed or was canceled.', 'error')

    def process_failed(self):
        logging.info("Process failed or was canceled.")
        self.is_running = False
        set_default_button_states(self)
        self.builder.get_object('progress_bar')['value'] = 0
        self.update_status('Process failed or was canceled.', 'error')

    def prompt_completion_tasks(self):
        tasks = []
        if self.quit_var.get():
            tasks.append('Quit the application')
        if self.import_oscar_var.get():
            tasks.append('Import data into OSCAR')

        if tasks:
            tasks_str = ' and '.join(tasks)
            msg = messagebox.askyesno('Completion Tasks', f'Do you want to {tasks_str}?')
            if msg:
                if self.import_oscar_var.get():
                    self.callbacks.import_cpap_data_with_oscar()
                if self.quit_var.get():
                    self.main_window.quit()
        else:
            # If neither task is selected, do nothing
            pass

    def handle_no_files(self):
        logging.info("No new files to transfer.")
        self.is_running = False
        set_default_button_states(self)
        self.builder.get_object('progress_bar')['value'] = 0
        tasks = []
        if self.quit_var.get():
            tasks.append('Quit the application')
        if self.import_oscar_var.get():
            tasks.append('Import data into OSCAR')

        if tasks:
            tasks_str = ' and '.join(tasks)
            msg = messagebox.askyesno('No New Files', f'No new files to transfer. Do you want to {tasks_str}?')
            if msg:
                if self.import_oscar_var.get():
                    self.callbacks.import_cpap_data_with_oscar()
                if self.quit_var.get():
                    self.main_window.quit()
        else:
            self.update_status('No new files to transfer.', 'info')

    def start_worker(self):
        # Create and start the worker thread with the current app context
        logging.info("Starting new worker thread.")
        self.worker = EzShareWorker(self.ezshare, self.worker_queue, name="EzShareWorkerThread", app=self)  # Pass self as app
        self.worker.start()

    def load_config(self):
        try:
            self.config_manager.load_config()
            self.apply_config_to_ui()
        except Exception as e:
            logging.error(f"Error loading config: {e}")

    def apply_config_to_ui(self):
        self.builder.get_object("local_directory_path").configure(path=self.config_manager.get_setting('Settings', 'path'))
        self.builder.get_object("url_entry").delete(0, tk.END)
        self.builder.get_object("url_entry").insert(0, self.config_manager.get_setting('Settings', 'url'))
        self.builder.get_object("ssid_entry").delete(0, tk.END)
        self.builder.get_object("ssid_entry").insert(0, self.config_manager.get_setting('WiFi', 'ssid'))
        self.builder.get_object("psk_entry").delete(0, tk.END)
        self.builder.get_object("psk_entry").insert(0, self.config_manager.get_setting('WiFi', 'psk'))
        self.quit_var.set(self.config_manager.get_setting('Settings', 'quit_after_completion') == 'True')
        self.import_oscar_var.set(self.config_manager.get_setting('Settings', 'import_oscar') == 'True')

    def run(self):
        logging.info("Starting main application loop")
        self.main_window.mainloop()

def run_gui():
    app = EzShareCPAPUI()
    app.run()
    return 0


def print_entrypoint_help():
    print(ENTRYPOINT_HELP)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] == 'gui':
        return run_gui()

    if argv[0] == 'sync':
        from cli import run_cli
        return run_cli(argv[1:])

    if argv[0] == '--cli':
        from cli import run_cli
        return run_cli(argv[1:])

    if argv[0] in ('-h', '--help'):
        print_entrypoint_help()
        return 0

    print_entrypoint_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
