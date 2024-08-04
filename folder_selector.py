import tkinter as tk
from tkinter import filedialog
import pygubu

import tkinter as tk
import pygubu

class FolderSelectorDialog:
    def __init__(self, master):
        self.master = master
        self.builder = pygubu.Builder()
        self.builder.add_from_file('ezsharecpap.ui')  # Load the UI definition from the XML file
        self.dialog = self.builder.get_object('folder_selector_window', self.master)

        # Define the entry widget variable and bind callbacks
        self.folder_path_var = self.builder.get_variable('folder_path_var')  # Ensure this variable is defined in Pygubu
        self.builder.connect_callbacks({
            'browse_folder': self.browse_folder,
            'confirm_selection': self.confirm_selection,
            'close_dialog': self.close_dialog
        })

    def browse_folder(self):
        folder_selected = tk.filedialog.askdirectory()
        if folder_selected:
            self.folder_path_var.set(folder_selected)

    def confirm_selection(self):
        folder_path = self.folder_path_var.get()
        print(f"Folder selected: {folder_path}")
        self.close_dialog()

    def close_dialog(self):
        self.dialog.destroy()

    def run(self):
        self.dialog.mainloop()

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()  # Optional: Hide the main window
    fsd = FolderSelectorDialog(root)
    fsd.run()


if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()  # Optional: withdraw the root window if the FolderSelectorDialog is not the main window
    app = FolderSelectorDialog(root)
    root.mainloop()
