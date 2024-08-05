import tkinter as tk
from tkinter import ttk
import pygubu
import threading
from wifi_utils import connect_to_wifi, disconnect_from_wifi
from ezshare import ezShare
from file_ops import list_dir
from status_manager import update_status
import urllib.parse
import logging

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

        # Load icons without scaling
        self.folder_icon = tk.PhotoImage(file="folder.png")
        self.file_icon = tk.PhotoImage(file="file.png")
        self.sd_card_icon = tk.PhotoImage(file="sdcard.png")

        # Set Treeview font size to 14 and row height to 18
        self.style = ttk.Style()
        self.style.configure("Treeview", font=("Arial", 14))
        self.style.configure("Treeview", rowheight=18)

        # Initialize ezShare instance
        self.ezshare = ezShare()

        # Status timer
        self.status_timer = None
        self.dialog_running = False  # Add dialog running flag

        logging.debug("FolderSelectorDialog initialized")

    def populate_treeview_with_http(self):
        logging.debug("Starting to populate treeview with HTTP")
        # Connect to Wi-Fi and traverse HTTP server in a separate thread to avoid blocking the UI
        threading.Thread(target=self._connect_and_populate).start()

    def _connect_and_populate(self):
        logging.debug("Begin _connect_and_populate")
        if self.main_window.quitting:
            logging.debug("Quitting detected, aborting populate")
            return
        
        ssid = self.main_window.builder.get_object('ssid_entry').get()
        psk = self.main_window.builder.get_object('psk_entry').get()
        url = self.main_window.builder.get_object('url_entry').get()

        logging.debug(f"SSID: {ssid}, PSK: {psk}, URL: {url}")  # Debugging statement

        if not url:
            self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'URL is empty. Please provide a valid URL.', 'error'))
            return

        try:
            self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Connecting to ez Share Wi-Fi.'))
            connect_to_wifi(self.ezshare, ssid, psk)
            if self.main_window.quitting:  # Check if the application is quitting
                logging.debug("Quitting detected after connecting, aborting")
                return
            self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Connected to ez Share Wi-Fi.'))

            # Clear the treeview
            logging.debug("Clearing the treeview")
            for item in self.treeview.get_children():
                self.treeview.delete(item)

            # Populate treeview with HTTP server contents
            logging.debug("Populating treeview with HTTP server contents")
            root_node = self.treeview.insert('', 'end', text='ez Share® Wi-Fi SD card', open=True, image=self.sd_card_icon)
            self._populate_treeview_node(root_node, url)

            if self.main_window.quitting:  # Check again before finalizing
                logging.debug("Quitting detected during population, aborting")
                return

            self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Populated treeview with HTTP server contents.'))
        except RuntimeError as e:
            if self.main_window.quitting:
                logging.debug(f"Quitting detected after RuntimeError: {e}")
                return
            self.main_window.main_window.after(0, lambda: update_status(self.main_window, f'Failed to connect to Wi-Fi: {e}', 'error'))
        finally:
            disconnect_from_wifi(self.ezshare)
            # Show the dialog after populating the treeview if not quitting
            if not self.main_window.quitting:
                logging.debug("Showing dialog after populating treeview")
                self.dialog_running = True
                self.dialog.deiconify()

    def _populate_treeview_node(self, parent, url):
        if self.main_window.quitting:
            logging.debug("Quitting detected, aborting node population")
            return
        
        try:
            files, dirs = list_dir(self.ezshare, url)
            logging.debug(f"Directories found: {dirs}")
            logging.debug(f"Files found: {files}")
            for dirname, dir_url in dirs:
                node_id = self.treeview.insert(parent, 'end', text=' ' + dirname, open=False, image=self.folder_icon)
                self._populate_treeview_node(node_id, urllib.parse.urljoin(url, dir_url))
            for file_info in files:
                filename, file_url = file_info[:2]  # Unpack only the first two elements
                self.treeview.insert(parent, 'end', text=' ' + filename, image=self.file_icon)
        except Exception as e:
            logging.error(f"Error populating treeview node: {e}")

    def reset_status(self):
        self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Ready.', 'info'))

    def close_dialog(self, event=None):
        logging.debug("Closing folder selector dialog")
        self.dialog_running = False
        self.dialog.destroy()

    def confirm_selection(self, event=None):
        folder_path = self.folder_path_var.get()
        logging.debug(f"Folder selected: {folder_path}")
        self.close_dialog()

    def run(self):
        logging.debug("Running folder selector dialog")
        self.populate_treeview_with_http()
        self.dialog.mainloop()
