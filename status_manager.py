# status_manager.py
import logging
import threading
from utils import set_default_button_states, update_button_state

status_lock = threading.Lock()


def update_status(app, message, message_type='info', target_app=None, restored_ssid=None):
    target = target_app if target_app else app
    if not target or not hasattr(target, 'builder'):
        logging.error("Cannot update status: app or builder is None or improperly passed.")
        return

    current_status = target.builder.get_object('status_label')['text']
    logging.info(
        "Requested status update from %r to %r with type %r",
        current_status,
        message,
        message_type,
    )

    with status_lock:
        if message != current_status:
            if hasattr(target, 'status_timer') and target.status_timer:
                try:
                    get_window(target).after_cancel(target.status_timer)
                except Exception as e:
                    logging.error(f"Failed to cancel existing status timer: {e}")
                target.status_timer = None

            # Optionally show which SSID we restored to (passed by callers)
            if restored_ssid:
                message = f"{message} (restored to '{restored_ssid}')"
                logging.info("Wi‑Fi restore target (previous SSID): %r", restored_ssid)

            target.builder.get_object('status_label')['text'] = message
            set_status_colour(target, message_type)
            log_status(message, message_type)

            if message_type == 'info' and message != 'Ready.':
                # Set a delay to reset status to "Ready." only when no other operation is running
                target.status_timer = get_window(target).after(5000, lambda: reset_status(target))
            elif message_type == 'info' and message == 'Ready.':
                # Reset only if nothing is running
                if not target.is_running:
                    target.status_timer = None
                    set_default_button_states(target)
                    update_button_state(target, 'start_button', enabled=True, is_default=True)
                    update_button_state(target, 'quit_button', enabled=True)


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
            logging.info("Status is 'Ready.' Resetting button states to default.")
            set_default_button_states(app)  # Reset button states to default when Ready

            # Explicitly ensure critical buttons are correctly set
            logging.info("Explicitly ensuring 'start_button' and 'quit_button' are enabled.")
            update_button_state(app, 'start_button', enabled=True, is_default=True)
            update_button_state(app, 'quit_button', enabled=True)
