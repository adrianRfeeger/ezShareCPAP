import os
import configparser
import tkinter as tk

DEFAULT_CONFIG = {
    'Settings': {
        'path': '~/Documents/CPAP_Data/SD_card',
        'url': 'http://192.168.4.1/dir?dir=A:',
        'import_oscar': 'False',
        'quit_after_completion': 'False'
    },
    'WiFi': {
        'ssid': 'ez Share',
        'psk': '88888888'
    },
    'Window': {
        'x': '100',
        'y': '100'
    }
}

def init_config(config_file):
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        config.read_dict(DEFAULT_CONFIG)
        save_config(config, config_file)
    else:
        config.read(config_file)
        for section, values in DEFAULT_CONFIG.items():
            if section not in config:
                config[section] = values
            else:
                for key, value in values.items():
                    if key not in config[section]:
                        config[section][key] = value
    return config

def save_config(config, config_file):
    try:
        with open(config_file, 'w') as configfile:
            config.write(configfile)
    except IOError as e:
        print(f"Error saving config file: {e}")

def restore_defaults_ui(config, builder, quit_var, import_oscar_var, update_status):
    config.read_dict(DEFAULT_CONFIG)
    apply_config_to_ui(config, builder, quit_var, import_oscar_var)
    update_status('Settings have been restored to defaults.', 'info')

def apply_config_to_ui(config, builder, quit_var, import_oscar_var):
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

    quit_var.set(config['Settings'].getboolean('quit_after_completion', False))
    import_oscar_var.set(config['Settings'].getboolean('import_oscar', False))

def load_config(config, builder, quit_var, import_oscar_var, mainwindow):
    apply_config_to_ui(config, builder, quit_var, import_oscar_var)
    set_window_location(config, mainwindow)

def save_config_ui(config, builder, config_file, mainwindow, quit_var, import_oscar_var, update_status):
    pathchooser = builder.get_object('path')
    config['Settings']['path'] = pathchooser.cget('path')
    config['Settings']['url'] = builder.get_object('urlEntry').get()
    config['Settings']['import_oscar'] = str(import_oscar_var.get())
    config['Settings']['quit_after_completion'] = str(quit_var.get())
    config['WiFi']['ssid'] = builder.get_object('ssidEntry').get()
    config['WiFi']['psk'] = builder.get_object('pskEntry').get()
    save_window_location(config, mainwindow)
    save_config(config, config_file)
    update_status('Settings have been saved.', 'info')

def set_window_location(config, window):
    x = config['Window'].get('x', '100')
    y = config['Window'].get('y', '100')
    window.geometry(f'+{x}+{y}')

def save_window_location(config, window):
    x = window.winfo_x()
    y = window.winfo_y()
    config['Window'] = {
        'x': x,
        'y': y
    }
