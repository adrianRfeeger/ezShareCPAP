import tkinter as tk
from tkinter import ttk
from wifi_utils import connect_to_wifi, disconnect_from_wifi, wifi_connected
from file_ops import list_dir
from status_manager import update_status
import logging
import urllib.parse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class FolderSelector:
    def __init__(self, app):
        self.app = app

    def open_folder_selector(self):
        update_status(self.app, 'Opening folder selector...', 'info')
        logger.info('Opening folder selector...')
        self.app.folder_selector_window.deiconify()
        self.populate_folder_selector()

    def populate_folder_selector(self):
        if not self.app.ezshare.url:
            update_status(self.app, "URL is not set. Please set the URL and try again.", 'error')
            logger.error("URL is not set. Please set the URL and try again.")
            return

        try:
            update_status(self.app, 'Connecting to ez Share Wi-Fi...', 'info')
            logger.info('Connecting to ez Share Wi-Fi...')
            self.set_ezshare_params()
            connect_to_wifi(self.app.ezshare)
            if not wifi_connected(self.app.ezshare):
                update_status(self.app, 'Failed to connect to ez Share Wi-Fi.', 'error')
                logger.error('Failed to connect to ez Share Wi-Fi.')
                return

            update_status(self.app, 'Fetching folder structure...', 'info')
            logger.info('Fetching folder structure...')
            self.fetch_directory_structure()
        except Exception as e:
            update_status(self.app, f"Failed to fetch folders: {e}", 'error')
            logger.error(f"Failed to fetch folders: {e}")
        finally:
            disconnect_from_wifi(self.app.ezshare)
            logger.info('Disconnected from ez Share Wi-Fi.')

    def set_ezshare_params(self):
        self.app.ezshare.set_params(
            path=self.app.config_manager.get_setting('Settings', 'path'),
            url=self.app.config_manager.get_setting('Settings', 'url'),
            start_time=None,
            show_progress=True,
            verbose=True,
            overwrite=False,
            keep_old=False,
            ssid=self.app.builder.get_object('ssid_entry').get(),
            psk=self.app.builder.get_object('psk_entry').get(),
            ignore=[],
            retries=3,
            connection_delay=5,
            debug=True
        )
        logger.debug("Parameters set for ezShare.")

    def fetch_directory_structure(self):
        treeview = self.app.builder.get_object('folder_select')
        treeview.delete(*treeview.get_children())

        if treeview:
            logger.debug("Treeview object found")
        else:
            logger.error("Treeview object not found")

        def populate_treeview(url, parent=""):
            files, dirs = list_dir(self.app.ezshare, url)
            logger.debug(f"Fetched {len(dirs)} directories and {len(files)} files from {url}")

            # Log directories and files
            for dirname, dir_url in dirs:
                logger.debug(f"Directory: {dirname} - URL: {dir_url}")
                dir_id = treeview.insert(parent, 'end', text=dirname, values=(dir_url,))
                logger.debug(f"Inserted directory '{dirname}' with id '{dir_id}'")
                absolute_dir_url = urllib.parse.urljoin(url, dir_url)
                populate_treeview(absolute_dir_url, dir_id)

            for filename, file_url, _ in files:
                logger.debug(f"File: {filename} - URL: {file_url}")
                treeview.insert(parent, 'end', text=filename, values=(file_url,))
                logger.debug(f"Inserted file '{filename}'")

        populate_treeview(self.app.ezshare.url)
        # Explicitly refresh the Treeview
        treeview.update_idletasks()
        update_status(self.app, 'Folder structure loaded successfully.', 'info')
        logger.info('Folder structure loaded successfully.')

    def confirm_selection(self, event=None):
        treeview = self.app.builder.get_object('folder_select')
        selected_item = treeview.selection()
        if selected_item:
            folder_name = treeview.item(selected_item)['text']
            self.app.builder.get_object('url_entry').delete(0, tk.END)
            self.app.builder.get_object('url_entry').insert(0, f"{self.app.ezshare.url}/{folder_name}")
            self.app.folder_selector_window.withdraw()
            update_status(self.app, f'Selected folder: {folder_name}', 'info')
            logger.info(f'Selected folder: {folder_name}')
        else:
            update_status(self.app, "No folder selected. Please select a folder.", 'warning')
            logger.warning("No folder selected. Please select a folder.")
        disconnect_from_wifi(self.app.ezshare)
        logger.info('Disconnected from ez Share Wi-Fi.')

    def cancel_folder_selection(self, event=None):
        self.app.folder_selector_window.withdraw()
        disconnect_from_wifi(self.app.ezshare)
        update_status(self.app, 'Folder selection cancelled.', 'info')
        logger.info('Folder selection cancelled.')

    def run(self):
        self.open_folder_selector()
