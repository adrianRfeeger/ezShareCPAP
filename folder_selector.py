import os
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import pygubu

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

        # Populate the Treeview with the current directory contents
        self.populate_treeview(os.getcwd())

    def populate_treeview(self, path):
        # Clear the treeview
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # Add root folder
        root_node = self.treeview.insert('', 'end', text=path, open=True)
        self.populate_treeview_node(root_node, path)

    def populate_treeview_node(self, parent_node, path):
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            node = self.treeview.insert(parent_node, 'end', text=entry, open=False)
            if os.path.isdir(entry_path):
                self.populate_treeview_node(node, entry_path)

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

    def run(self):
        self.dialog.mainloop()

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()  # Optional: Hide the main window
    fsd = FolderSelectorDialog(root)
    fsd.run()
