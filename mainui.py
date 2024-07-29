#!/usr/bin/python3
import pathlib
import tkinter as tk
import pygubu

PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "ezshare.ui"
RESOURCE_PATHS = [PROJECT_PATH]


class ezShareGuiUI:
    def __init__(self, master=None):
        self.builder = pygubu.Builder()
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(PROJECT_UI)
        # Main widget
        self.mainwindow: tk.Toplevel = self.builder.get_object(
            "mainwindow", master)
        self.builder.connect_callbacks(self)

    def run(self):
        self.mainwindow.mainloop()

    def ez_share_config(self, event=None):
        pass

    def open_oscar_download_page(self, event=None):
        pass

    def save_config(self, event=None):
        pass

    def restore_defaults(self, event=None):
        pass

    def start_process(self, event=None):
        pass

    def cancel_process(self, event=None):
        pass

    def quit_application(self, event=None):
        pass


if __name__ == "__main__":
    app = ezShareGuiUI()
    app.run()
