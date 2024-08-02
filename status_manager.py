import logging
import tkinter as tk
from tkinter import messagebox

def update_status(app, message, message_type='info'):
    current_status = app.builder.get_object('statusLabel')['text']
    if message != current_status:
        app.builder.get_object('statusLabel')['text'] = message
        if message_type == 'error':
            app.builder.get_object('statusLabel')['foreground'] = 'red'
            logging.error(message)
            messagebox.showerror("Error", message)
        else:
            app.builder.get_object('statusLabel').config(foreground='')
            logging.info(message)
        if message_type == 'info' and message != 'Ready.':
            app.status_timer = app.mainwindow.after(5000, app.reset_status)
