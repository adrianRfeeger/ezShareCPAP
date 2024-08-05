import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import pygubu
import threading
from wifi_utils import connect_to_wifi, disconnect_from_wifi
from ezshare import ezShare

class FolderSelectorDialog:
    def __init__(self, master):
        self.master = master
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

        # Populate the Treeview with the HTTP server contents
        self.populate_treeview_with_http()

    def populate_treeview_with_http(self):
        # Connect to Wi-Fi and traverse HTTP server in a separate thread to avoid blocking the UI
        threading.Thread(target=self._connect_and_populate).start()

    def _connect_and_populate(self):
        ssid = self.builder.get_object('ssid_entry').get()
        psk = self.builder.get_object('psk_entry').get()
        url = self.builder.get_object('url_entry').get()

        try:
            connect_to_wifi(self.ezshare, ssid, psk)
            self.update_status('Connected to ez Share Wi-Fi.')

            # Clear the treeview
            for item in self.treeview.get_children():
                self.treeview.delete(item)

            # Populate treeview with HTTP server contents
            self._populate_treeview_node('', url)

            self.update_status('Populated treeview with HTTP server contents.')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to Wi-Fi: {e}")
        finally:
            disconnect_from_wifi(self.ezshare)
            self.update_status('Disconnected from ez Share Wi-Fi.')

    def _populate_treeview_node(self, parent_node, url):
        # Here you will use the existing ezShare methods to traverse the HTTP server
        files, dirs = self.ezshare.list_dir(url)
        for filename, file_url, file_ts in files:
            self.treeview.insert(parent_node, 'end', text=filename, open=False)
        for dirname, dir_url in dirs:
            node = self.treeview.insert(parent_node, 'end', text=dirname, open=False)
            self._populate_treeview_node(node, dir_url)

    def browse_folder(self, event=None):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            self.populate_treeview(folder_selected)

    def confirm_selection(self, event=None):
        folder_path = self.folder_path_var.get()
        print(f"Folder selected: {folder_path}")
        self.close_dialog()

    def close_dialog(self, event=None):
        self.dialog.destroy()

    def update_status(self, message):
        print(message)

    def run(self):
        self.dialog.mainloop()

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()  # Optional: Hide the main window
    fsd = FolderSelectorDialog(root)
    fsd.run()
