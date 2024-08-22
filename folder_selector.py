import tkinter as tk
from tkinter import ttk, TclError  # Import TclError here
import pygubu
import threading
from wifi_utils import connect_to_wifi, disconnect_wifi
from ezshare import ezShare
from file_ops import list_dir
from status_manager import update_status
from utils import resource_path
import logging

class FolderSelectorDialog:
    def __init__(self, master, main_window):
        self.master = master
        self.main_window = main_window  # This should be the main application instance
        self.builder = pygubu.Builder()
        self.builder.add_from_file(resource_path('ezsharecpap.ui'))  # Load the UI definition from the XML file
        self.dialog = self.builder.get_object('folder_selector_window', self.master)

        # Initialize the status timer to None
        self.status_timer = None
        self.thread_lock = threading.Lock()  # Lock to ensure thread synchronization
        self.current_thread = None  # Track the currently running thread
        self.stop_thread = False  # Flag to stop thread

        # Retrieve the variable from the hidden Entry
        self.folder_path_var = self.builder.get_variable('folder_path_var')

        # Connect the callbacks
        self.builder.connect_callbacks(self)

        # Initialize the Treeview
        self.treeview = self.builder.get_object('folder_select')

        # Load icons 
        self.folder_icon = tk.PhotoImage(file=resource_path("folder.png"))
        self.file_icon = tk.PhotoImage(file=resource_path("file.png"))
        self.sdcard_icon = tk.PhotoImage(file=resource_path("sdcard.png"))

        # Set Treeview font size to 14 and row height to 18
        self.style = ttk.Style()
        self.style.configure("Treeview", font=("Arial", 14))
        self.style.configure("Treeview", rowheight=18)

        # Initialize ezShare instance
        self.ezshare = ezShare()

        # Bind the selection event to control selection
        self.treeview.bind('<<TreeviewSelect>>', self.on_treeview_select)

    def populate_treeview_with_http(self):
        # Hide the dialog before populating the Treeview
        self.dialog.withdraw()
        # Set the `is_running` flag to True to suppress the "Ready" status
        self.main_window.is_running = True
        # Check if there's already an active thread and stop it
        with self.thread_lock:
            if self.current_thread and self.current_thread.is_alive():
                logging.info(f"Waiting for existing thread {self.current_thread.name} to finish.")
                self.stop_thread = True
                self.current_thread.join()  # Wait for the thread to finish

            # Start a new thread with a specific name
            self.stop_thread = False
            self.current_thread = threading.Thread(target=self._connect_and_populate, name="FolderSelectorThread")
            self.current_thread.start()

    def _connect_and_populate(self):
        ssid = self.main_window.builder.get_object('ssid_entry').get()
        psk = self.main_window.builder.get_object('psk_entry').get()
        base_url = 'http://192.168.4.1/dir?dir=A:'
        interface = None

        try:
            self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Connecting to ez Share Wi-Fi...'))
            interface = connect_to_wifi(ssid, psk)
            
            # Check if the process was canceled before proceeding
            if not interface or self.stop_thread or not self.main_window.is_running:
                raise RuntimeError("Failed to connect or process was canceled.")

            self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Connected to ez Share Wi-Fi.'))

            # Clear the treeview only if it exists
            if self.treeview.winfo_exists() and not self.stop_thread:
                self.main_window.main_window.after(0, lambda: self.clear_treeview())

            # Populate treeview with HTTP server contents
            if self.treeview.winfo_exists() and not self.stop_thread:
                self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'Retrieving ez Share SD card directory information...'))
                root_node = self.treeview.insert('', 'end', text=' ez Share® Wi-Fi SD card', open=True, image=self.sdcard_icon, tags=('folder', base_url))
                self.main_window.main_window.after(0, lambda: self._populate_treeview_node(root_node, base_url))
                self.main_window.main_window.after(0, lambda: update_status(self.main_window, 'ez Share SD card directory information retrieved.'))

        except RuntimeError as e:
            # Capture 'e' inside the lambda to ensure it is accessible within the lambda's scope
            error_message = f'Failed to connect to Wi-Fi or process canceled: {e}'
            self.main_window.main_window.after(0, lambda: update_status(self.main_window, error_message, 'error'))
        finally:
            if interface:
                self.main_window.main_window.after(0, lambda: disconnect_wifi(ssid, interface))
            self.main_window.main_window.after(0, self.ensure_treeview_populated)

            # Set the `is_running` flag to False, allowing the "Ready" status to be set
            self.main_window.is_running = False
            self.main_window.main_window.after(0, self.set_status_ready_with_timer)

    def clear_treeview(self):
        for item in self.treeview.get_children():
            self.treeview.delete(item)

    def _populate_treeview_node(self, parent, url):
        try:
            # Ensure the Treeview widget still exists before performing operations on it
            if not self.treeview.winfo_exists() or self.stop_thread:
                logging.warning("Treeview no longer exists or thread stopped, aborting population.")
                return

            # Fetch files and directories using list_dir
            files, dirs = list_dir(self.ezshare, url)

            # Populate directories first
            for dirname in dirs:
                full_dir_url = url + '/' + dirname[0]  # Access the first element of the tuple
                node_id = self.treeview.insert(parent, 'end', text=' ' + dirname[0], open=False, image=self.folder_icon, tags=('folder', full_dir_url))
                self._populate_treeview_node(node_id, full_dir_url)

            # Then populate files
            for filename in files:
                full_file_url = url + '/' + filename[0]  # Access the first element of the tuple
                self.treeview.insert(parent, 'end', text=' ' + filename[0], image=self.file_icon, tags=('file', full_file_url))

        except TclError as e:
            logging.error(f"Error during Treeview population: {e}")

    def ensure_treeview_populated(self):
        if not self.treeview.winfo_exists():
            logging.info("Treeview no longer exists, aborting file population.")
            return

        # Check if the treeview has more than one item (excluding the root node)
        if len(self.treeview.get_children('')) > 0:
            self.main_window.main_window.after(0, self.show_dialog)
        else:
            # Retry after a short delay if not populated yet
            self.main_window.main_window.after(100, self.ensure_treeview_populated)

    def show_dialog(self):
        if self.dialog.winfo_exists():
            self.dialog.deiconify()
            self.dialog.lift()

    def set_status_ready_with_timer(self):
        # Cancel any existing timer
        if self.status_timer:
            self.main_window.main_window.after_cancel(self.status_timer)
        
        # Set a new timer to reset status to "Ready."
        self.status_timer = self.main_window.main_window.after(5000, self.reset_status)

    def reset_status(self):
        # Reset status to "Ready." if no other operation is in progress
        if not self.main_window.is_running:
            update_status(self.main_window, 'Ready.', 'info')
            self.status_timer = None

    def close_dialog(self, event=None):
        if self.dialog.winfo_exists():
            self.dialog.destroy()
        self.main_window.enable_ui_elements()

        # Disable the cancel button after closing the dialog
        self.main_window.callbacks.buttons_active['cancel'] = False
        self.main_window.builder.get_object('cancel_button').config(state=tk.DISABLED)

    def confirm_selection(self, event=None):
        selected_item = self.treeview.selection()
        if selected_item:
            item_tag = self.treeview.item(selected_item, 'tags')[0]
            if item_tag == 'folder':
                folder_url = self.treeview.item(selected_item, 'tags')[1]
                # Enable the url_entry field
                url_entry = self.main_window.builder.get_object('url_entry')
                url_entry.config(state=tk.NORMAL)  # Enable the field

                # Set the URL directly in the entry field
                url_entry.delete(0, tk.END)
                url_entry.insert(0, folder_url)
        self.close_dialog()

    def on_treeview_select(self, event):
        selected_item = self.treeview.selection()
        if selected_item:
            item_tag = self.treeview.item(selected_item, 'tags')[0]
            if item_tag == 'file':
                self.treeview.selection_remove(selected_item)

    def run(self):
        self.populate_treeview_with_http()
        self.dialog.mainloop()

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()  # Optional: Hide the main window
    fsd = FolderSelectorDialog(root, root)
    fsd.run()
