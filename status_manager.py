import logging
import threading

status_lock = threading.Lock()  # Ensure thread-safe status updates

def update_status(app, message, message_type='info', target_app=None):
    target = target_app if target_app else app
    current_status = target.builder.get_object('status_label')['text']
    logging.info(f"Requested status update from '{current_status}' to '{message}' with type '{message_type}'")
    
    with status_lock:
        if message != current_status:
            if hasattr(target, 'status_timer') and target.status_timer:
                logging.info("Cancelling existing status timer before updating status.")
                try:
                    get_window(target).after_cancel(target.status_timer)
                except Exception as e:
                    logging.error(f"Failed to cancel existing status timer: {e}")
                target.status_timer = None

            target.builder.get_object('status_label')['text'] = message
            set_status_colour(target, message_type)
            log_status(message, message_type)

            if message_type == 'info' and message != 'Ready.':
                logging.info("Setting new status timer to reset status to 'Ready.'")
                target.status_timer = get_window(target).after(5000, lambda: reset_status(target))
            elif message_type == 'info' and message == 'Ready.':
                if not target.is_running:  # Ensure not overriding ongoing operations
                    logging.info("Setting status to 'Ready.' and ensuring no active timers.")
                    target.status_timer = None

def set_status_colour(app, message_type):
    if message_type == 'error':
        app.builder.get_object('status_label')['foreground'] = 'red'
    else:
        app.builder.get_object('status_label').config(foreground='')

def log_status(message, message_type):
    if message_type == 'error':
        logging.error(message)
    else:
        logging.info(message)

def get_window(app):
    if hasattr(app, 'main_window'):
        return app.main_window
    elif hasattr(app, 'dialog'):
        return app.dialog
    else:
        raise AttributeError("The app object does not have 'main_window' or 'dialog' attribute.")

def reset_status(app):
    logging.info("Resetting status to 'Ready.'")
    with status_lock:
        if hasattr(app, 'status_timer') and app.status_timer:
            try:
                get_window(app).after_cancel(app.status_timer)
                logging.info("Status timer cancelled successfully during reset.")
            except Exception as e:
                logging.error(f"Failed to cancel status timer during reset: {e}")
            app.status_timer = None
        if not app.is_running:
            app.builder.get_object('status_label')['text'] = 'Ready.'
            set_status_colour(app, 'info')
