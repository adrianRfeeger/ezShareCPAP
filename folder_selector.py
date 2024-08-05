import tkinter as tk
from tkinter import ttk
import pygubu
import threading
from wifi_utils import connect_to_wifi, disconnect_from_wifi
from ezshare import ezShare
from file_ops import list_dir
from status_manager import update_status, set_status_colour, log_status
import urllib.parse

class FolderSelectorDialog:
    def __init__(self, master, main_window):
        self.master = master
        self.main_window = main_window  # Store reference to main window
        self.builder = pygubu.Builder()
        self.builder.add_from_file('ezsharecpap.ui')  # Load the UI definition from the XML file
        self.dialog = self.builder.get_object('folder_selector_window', self.master)

        # Retrieve the variable from the hidden Entry
        self.folder_path_var = self.builder.get_variable('folder_path_var')

        # Connect the callbacks
        self.builder.connect_callbacks(self)

        # Initialize the Treeview
        self.treeview = self.builder.get_object('folder_select')

        # Initialize ezShare instance
        self.ezshare = ezShare()

        # Status timer
        self.status_timer = None

        # Populate the Treeview with the HTTP server contents
        self.populate_treeview_with_http()

    def populate_treeview_with_http(self):
        # Connect to Wi-Fi and traverse HTTP server in a separate thread to avoid blocking the UI
        threading.Thread(target=self._connect_and_populate).start()

    def _connect_and_populate(self):
        ssid = self.main_window.builder.get_object('ssid_entry').get()
        psk = self.main_window.builder.get_object('psk_entry').get()
        url = self.main_window.builder.get_object('url_entry').get()

        print(f"SSID: {ssid}, PSK: {psk}, URL: {url}")  # Debugging statement

        if not url:
            update_status(self, 'URL is empty. Please provide a valid URL.', 'error', target_app=self.main_window)
            return

        try:
            connect_to_wifi(self.ezshare, ssid, psk)
            update_status(self, 'Connected to ez Share Wi-Fi.', target_app=self.main_window)

            # Clear the treeview
            for item in self.treeview.get_children():
                self.treeview.delete(item)

            # Populate treeview with HTTP server contents
            self._populate_treeview_node('', url)

            update_status(self, 'Populated treeview with HTTP server contents.', target_app=self.main_window)
        except RuntimeError as e:
            update_status(self, f'Failed to connect to Wi-Fi: {e}', 'error', target_app=self.main_window)
        finally:
            disconnect_from_wifi(self.ezshare)

    def _populate_treeview_node(self, parent, url):
        files, dirs = list_dir(self.ezshare, url)
        for dirname, dir_url in dirs:
            node_id = self.treeview.insert(parent, 'end', text=dirname, open=False)
            self._populate_treeview_node(node_id, urllib.parse.urljoin(url, dir_url))
        for filename, file_url, file_ts in files:
            self.treeview.insert(parent, 'end', text=filename)

    def reset_status(self):
        update_status(self.main_window, 'Ready.', 'info')

    def close_dialog(self, event=None):
        self.dialog.destroy()

    def confirm_selection(self, event=None):
        folder_path = self.folder_path_var.get()
        print(f"Folder selected: {folder_path}")
        self.close_dialog()

    def run(self):
        self.dialog.deiconify()
        self.dialog.mainloop()
