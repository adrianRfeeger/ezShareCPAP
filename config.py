import os
import configparser
import tkinter as tk

def init_config(config_file):
    """
    Initialize the configuration file. If it doesn't exist, create it with default settings.
    """
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        config['Settings'] = {
            'path': '~/Documents/CPAP_Data/SD_card',
            'url': 'http://192.168.4.1/dir?dir=A:',
            'import_oscar': 'False',
            'quit_after_completion': 'False'
        }
        config['WiFi'] = {
            'ssid': 'ez Share',
            'psk': '88888888'
        }
        config['Window'] = {
            'x': '100',
            'y': '100'
        }
        with open(config_file, 'w') as configfile:
            config.write(configfile)
    else:
        config.read(config_file)
        if 'Settings' not in config:
            config['Settings'] = {
                'path': '~/Documents/CPAP_Data/SD_card',
                'url': 'http://192.168.4.1/dir?dir=A:',
                'import_oscar': 'False',
                'quit_after_completion': 'False'
            }
        if 'WiFi' not in config:
            config['WiFi'] = {
                'ssid': 'ez Share',
                'psk': '88888888'
            }
        if 'Window' not in config:
            config['Window'] = {
                'x': '100',
                'y': '100'
            }
    return config


def save_config(config, config_file):
    """
    Save the current configuration to the specified file.
    """
    with open(config_file, 'w') as configfile:
        config.write(configfile)


def restore_defaults_ui(config, builder, quit_var, import_oscar_var, update_status):
    """
    Restore the configuration to its default values and update the UI.
    """
    config['Settings'] = {
        'path': '~/Documents/CPAP_Data/SD_card',
        'url': 'http://192.168.4.1/dir?dir=A:',
        'import_oscar': 'False',
        'quit_after_completion': 'False'
    }
    config['WiFi'] = {
        'ssid': 'ez Share',
        'psk': '88888888'
    }
    config['Window'] = {
        'x': '100',
        'y': '100'
    }

    path_field = builder.get_object("path")
    path_field.configure(path=config['Settings']['path'])

    url_entry = builder.get_object("urlEntry")
    url_entry.delete(0, tk.END)
    url_entry.insert(0, config['Settings']['url'])

    ssid_entry = builder.get_object("ssidEntry")
    ssid_entry.delete(0, tk.END)
    ssid_entry.insert(0, config['WiFi']['ssid'])

    psk_entry = builder.get_object("pskEntry")
    psk_entry.delete(0, tk.END)
    psk_entry.insert(0, config['WiFi']['psk'])

    quit_var.set(False)
    import_oscar_var.set(False)

    update_status('Settings have been restored to defaults.', 'info')


def load_config(config, builder, quit_var, import_oscar_var, mainwindow):
    """
    Load the configuration into the UI.
    """
    pathchooser = builder.get_object('path')
    pathchooser.configure(path=config['Settings'].get('path', '~/Documents/CPAP_Data/SD_card'))
    builder.get_object('urlEntry').insert(0, config['Settings'].get('url', 'http://192.168.4.1/dir?dir=A:'))
    builder.get_object('ssidEntry').insert(0, config['WiFi'].get('ssid', 'ez Share'))
    builder.get_object('pskEntry').insert(0, config['WiFi'].get('psk', '88888888'))
    quit_var.set(config['Settings'].getboolean('quit_after_completion', False))
    import_oscar_var.set(config['Settings'].getboolean('import_oscar', False))
    set_window_location(config, mainwindow)


def save_config_ui(config, builder, config_file, mainwindow, quit_var, import_oscar_var, update_status):
    """
    Save the UI settings to the configuration.
    """
    pathchooser = builder.get_object('path')
    config['Settings'] = {
        'path': pathchooser.cget('path'),
        'url': builder.get_object('urlEntry').get(),
        'import_oscar': str(import_oscar_var.get()),
        'quit_after_completion': str(quit_var.get())
    }
    config['WiFi'] = {
        'ssid': builder.get_object('ssidEntry').get(),
        'psk': builder.get_object('pskEntry').get()
    }
    save_window_location(config, mainwindow)
    save_config(config, config_file)
    update_status('Settings have been saved.', 'info')


def set_window_location(config, window):
    """
    Set the window location based on the configuration.
    """
    x = config['Window'].get('x', '100')
    y = config['Window'].get('y', '100')
    window.geometry(f'+{x}+{y}')


def save_window_location(config, window):
    """
    Save the current window location to the configuration.
    """
    x = window.winfo_x()
    y = window.winfo_y()
    config['Window'] = {
        'x': x,
        'y': y
    }
