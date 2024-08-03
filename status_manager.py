import logging
from tkinter import messagebox

def update_status(app, message, message_type='info'):
    current_status = app.builder.get_object('status_label')['text']
    logging.info(f"Updating status from '{current_status}' to '{message}' with type '{message_type}'")
    if message != current_status:
        app.builder.get_object('status_label')['text'] = message
        set_status_colour(app, message_type)
        log_status(message, message_type)
        if message_type == 'info' and message != 'Ready.':
            if app.status_timer:
                logging.info("Cancelling existing status timer")
                app.main_window.after_cancel(app.status_timer)
            logging.info("Setting new status timer to reset status to 'Ready.'")
            app.status_timer = app.main_window.after(5000, app.reset_status)
        elif message_type == 'info' and message == 'Ready.':
            if app.status_timer:
                logging.info("Cancelling existing status timer for 'Ready.' message")
                app.main_window.after_cancel(app.status_timer)
            app.status_timer = None

def set_status_colour(app, message_type):
    if message_type == 'error':
        app.builder.get_object('status_label')['foreground'] = 'red'
    else:
        app.builder.get_object('status_label').config(foreground='')

def log_status(message, message_type):
    if message_type == 'error':
        logging.error(message)
        messagebox.showerror("Error", message)
    else:
        logging.info(message)
