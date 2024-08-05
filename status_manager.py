import logging
from tkinter import messagebox

def update_status(app, message, message_type='info', target_app=None):
    target = target_app if target_app else app
    current_status = target.builder.get_object('status_label')['text']
    logging.info(f"Updating status from '{current_status}' to '{message}' with type '{message_type}'")
    if message != current_status:
        target.builder.get_object('status_label')['text'] = message
        set_status_colour(target, message_type)
        log_status(message, message_type)
        if message_type == 'info' and message != 'Ready.':
            if hasattr(target, 'status_timer') and target.status_timer:
                logging.info("Cancelling existing status timer")
                get_window(target).after_cancel(target.status_timer)
            logging.info("Setting new status timer to reset status to 'Ready.'")
            target.status_timer = get_window(target).after(5000, target.reset_status)
        elif message_type == 'info' and message == 'Ready.':
            if hasattr(target, 'status_timer') and target.status_timer:
                logging.info("Cancelling existing status timer for 'Ready.' message")
                get_window(target).after_cancel(target.status_timer)
            target.status_timer = None

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

def get_window(app):
    if hasattr(app, 'main_window'):
        return app.main_window
    elif hasattr(app, 'dialog'):
        return app.dialog
    else:
        raise AttributeError("The app object does not have 'main_window' or 'dialog' attribute.")
