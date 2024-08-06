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

        # Bind the selection event to control selection
        self.treeview.bind('<<TreeviewSelect>>', self.on_treeview_select)

    def populate_treeview_with_http(self):
        # Hide the dialog before populating the Treeview
        self.dialog.withdraw()
        # Connect to Wi-Fi and traverse HTTP server in a separate thread to avoid blocking the UI
        threading.Thread(target=self._connect_and_populate).start()

    def _connect_and_populate(self):
        root = self.main_window.main_window  # Access the root window
        ssid = self.main_window.builder.get_object('ssid_entry').get()
        psk = self.main_window.builder.get_object('psk_entry').get()
        base_url = 'http://192.168.4.1/dir?dir=A:'

        print(f"SSID: {ssid}, PSK: {psk}, Base URL: {base_url}")  # Debugging statement

        try:
            root.after(0, lambda: update_status(self.main_window, 'Connecting to ez Share Wi-Fi...'))
            connect_to_wifi(self.ezshare, ssid, psk)
            root.after(0, lambda: update_status(self.main_window, 'Connected to ez Share Wi-Fi.'))

            # Clear the treeview
            for item in self.treeview.get_children():
                self.treeview.delete(item)

            # Populate treeview with HTTP server contents
            root.after(0, lambda: update_status(self.main_window, 'Retrieving ez Share SD card directory information...'))
            root_node = self.treeview.insert('', 'end', text=' ez Share® Wi-Fi SD card', open=True, image=self.sdcard_icon, tags=('folder', base_url))
            self._populate_treeview_node(root_node, base_url)

            root.after(0, lambda: update_status(self.main_window, 'ez Share SD card directory information retrieved.'))
        except RuntimeError as e:
            root.after(0, lambda: update_status(self.main_window, f'Failed to connect to Wi-Fi: {e}', 'error'))
        finally:
            disconnect_from_wifi(self.ezshare)
            # Show the dialog again after populating the Treeview
            root.after(0, self.ensure_treeview_populated)

    def _populate_treeview_node(self, parent, url):
        files, dirs = list_dir(self.ezshare, url)
        for dirname, dir_url, *_ in dirs:
            full_dir_url = urllib.parse.urljoin(url, dir_url)
            node_id = self.treeview.insert(parent, 'end', text=' ' + dirname, open=False, image=self.folder_icon, tags=('folder', full_dir_url))
            self._populate_treeview_node(node_id, full_dir_url)
        for filename, file_url, *_ in files:
            full_file_url = urllib.parse.urljoin(url, file_url)
            self.treeview.insert(parent, 'end', text=' ' + filename, image=self.file_icon, tags=('file', full_file_url))

    def ensure_treeview_populated(self):
        # Check if the treeview has more than one item (excluding the root node)
        if len(self.treeview.get_children('')) > 0:
            print("Treeview populated correctly.")
            self.show_dialog()
        else:
            print("Treeview not populated yet. Retrying...")
            # Retry after a short delay if not populated yet
            self.dialog.after(100, self.ensure_treeview_populated)

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
            item_tag = self.treeview.item(selected_item, 'tags')[0]
            if item_tag == 'folder':
                folder_url = self.treeview.item(selected_item, 'tags')[1]
                self.main_window.builder.get_object('url_entry').delete(0, tk.END)
                self.main_window.builder.get_object('url_entry').insert(0, folder_url)
                print(f"URL selected: {folder_url}")
        self.close_dialog()

    def on_treeview_select(self, event):
        selected_item = self.treeview.selection()
        if selected_item:
            item_tag = self.treeview.item(selected_item, 'tags')[0]
            if item_tag == 'file':
                self.treeview.selection_remove(selected_item)

    def run(self):
        self.populate_treeview_with_http()  # Populate the Treeview before showing the dialog
        self.dialog.mainloop()
