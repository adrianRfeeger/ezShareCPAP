import tkinter as tk
import tkinter.ttk as ttk


def setup_ttk_styles(master=None):
    my_font = ("arial", 14, "bold")

    style = ttk.Style(master)

    style.configure("primary.TButton",
                    font=my_font,
                    background="#4582EC")
