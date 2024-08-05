import tkinter as tk
from tkinter import ttk
import pygubu
import threading
from wifi_utils import connect_to_wifi, disconnect_from_wifi
from ezshare import ezShare
from file_ops import list_dir
from status_manager import update_status
from utils import resource_path
import urllib.parse

class FolderSelectorDialog:
    def __init__(self, master, main_window):
        self.master = master
        self.main_window = main_window  # Store reference to main window
        self.builder = pygubu.Builder()
        self.builder.add_from_file(resource_path('ezsharecpap.ui'))  # Load the UI definition from the XML file
        self.dialog = self.builder.get_object('folder_selector_window', self.master)

        # Retrieve the variable from the hidden Entry
        self.folder_path_var = self.builder.get_variable('folder_path_var')

        # Connect the callbacks
        self.builder.connect_callbacks(self)

        # Initialize the Treeview
        self.treeview = self.builder.get_object('folder_select')

        # Load icons without scaling
        self.folder_icon = tk.PhotoImage(file=resource_path("folder.png"))
        self.file_icon = tk.PhotoImage(file=resource_path("file.png"))
        self.sdcard_icon = tk.PhotoImage(file=resource_path("sdcard.png"))

        # Set Treeview font size to 14 and row height to 18
        self.style = ttk.Style()
        self.style.configure("Treeview", font=("Arial", 14))
        self.style.configure("Treeview", rowheight=18)

        # Initialize ezShare instance
        self.ezshare = ezShare()

        # Status timer
        self.status_timer = None

    def populate_treeview_with_http(self):
        # Hide the dialog before populating the Treeview
        self.dialog.withdraw()
        # Connect to Wi-Fi and traverse HTTP server in a separate thread to avoid blocking the UI
        threading.Thread(target=self._connect_and_populate).start()

    def _connect_and_populate(self):
        root = self.main_window.main_window  # Access the root window
        ssid = self.main_window.builder.get_object('ssid_entry').get()
        psk = self.main_window.builder.get_object('psk_entry').get()
        url = self.main_window.builder.get_object('url_entry').get()

        print(f"SSID: {ssid}, PSK: {psk}, URL: {url}")  # Debugging statement

        if not url:
            root.after(0, lambda: update_status(self.main_window, 'URL is empty. Please provide a valid URL.', 'error'))
            return

        try:
            root.after(0, lambda: update_status(self.main_window, 'Connecting to ez Share Wi-Fi...'))
            connect_to_wifi(self.ezshare, ssid, psk)
            root.after(0, lambda: update_status(self.main_window, 'Connected to ez Share Wi-Fi.'))

            # Clear the treeview
            root.after(0, self.clear_treeview)

            # Populate treeview with HTTP server contents
            root.after(0, lambda: update_status(self.main_window, 'Retrieving ez Share SD card directory information...'))
            root.after(0, lambda: self._populate_treeview_node(self.treeview.insert('', 'end', text=' ez Share® Wi-Fi SD card', open=True, image=self.sdcard_icon, tags=(url,)), url))

            root.after(0, lambda: update_status(self.main_window, 'ez Share SD card directory information retrieved.'))
        except RuntimeError as e:
            root.after(0, lambda: update_status(self.main_window, f'Failed to connect to Wi-Fi: {e}', 'error'))
        finally:
            disconnect_from_wifi(self.ezshare)
            # Show the dialog again after populating the Treeview
            root.after(0, self.show_dialog)

    def _populate_treeview_node(self, parent, url):
        files, dirs = list_dir(self.ezshare, url)
        for dirname, dir_url, *_ in dirs:
            full_dir_url = urllib.parse.urljoin(url, dir_url)
            node_id = self.treeview.insert(parent, 'end', text=' ' + dirname, open=False, image=self.folder_icon, tags=(full_dir_url,))
            self._populate_treeview_node(node_id, full_dir_url)
        for filename, file_url, *_ in files:
            full_file_url = urllib.parse.urljoin(url, file_url)
            self.treeview.insert(parent, 'end', text=' ' + filename, image=self.file_icon, tags=(full_file_url,))

    def clear_treeview(self):
        for item in self.treeview.get_children():
            self.treeview.delete(item)

    def show_dialog(self):
        self.dialog.deiconify()
        self.dialog.lift()

    def reset_status(self):
        self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Ready.', 'info'))

    def close_dialog(self, event=None):
        self.dialog.destroy()

    def confirm_selection(self, event=None):
        selected_item = self.treeview.selection()
        if selected_item:
            item_url = self.treeview.item(selected_item, 'tags')[0]
            print(f"URL selected: {item_url}")
            self.main_window.builder.get_object('url_entry').delete(0, tk.END)
            self.main_window.builder.get_object('url_entry').insert(0, item_url)
        self.close_dialog()

    def run(self):
        self.populate_treeview_with_http()  # Populate the Treeview before showing the dialog
        self.dialog.mainloop()
