import tkinter as tk
from tkinter import filedialog
import pygubu

class FolderSelectorDialog:
    def __init__(self, master):
        self.master = master
        self.dialog = tk.Toplevel(self.master)
        self.dialog.title("Select Folder")
        self.dialog.transient(self.master)  # Set to be a transient window of the main application window
        self.dialog.geometry("400x400")  # Optional: Adjust size according to needs

        self.setup_widgets()

    def setup_widgets(self):
        self.label = tk.Label(self.dialog, text="Choose a folder:")
        self.label.pack(pady=10)

        self.path_var = tk.StringVar()
        self.entry = tk.Entry(self.dialog, textvariable=self.path_var, width=50)
        self.entry.pack(pady=10)

        self.browse_button = tk.Button(self.dialog, text="Browse...", command=self.browse_folder)
        self.browse_button.pack(pady=5)

        self.ok_button = tk.Button(self.dialog, text="OK", command=self.confirm_selection)
        self.ok_button.pack(pady=5)

        self.cancel_button = tk.Button(self.dialog, text="Cancel", command=self.dialog.destroy)
        self.cancel_button.pack(pady=5)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_var.set(folder_selected)

    def confirm_selection(self):
        # Here you can add code to handle the selected folder path
        folder_path = self.path_var.get()
        print(f"Folder selected: {folder_path}")  # Placeholder for your own functionality
        self.dialog.destroy()  # Close the dialog

    def run(self):
        self.dialog.wait_window()  # Wait for the dialog to close

if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()  # Optional: withdraw the root window if the FolderSelectorDialog is not the main window
    app = FolderSelectorDialog(root)
    root.mainloop()
