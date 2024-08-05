import os
import configparser
import logging

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

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.config.read_dict(DEFAULT_CONFIG)
            self.save_config()
        else:
            self.config.read(self.config_file)
            self.merge_default_config()

    def merge_default_config(self):
        for section, values in DEFAULT_CONFIG.items():
            if section not in self.config:
                self.config[section] = values
            else:
                for key, value in values.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value

    def save_config(self):
        try:
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)
        except IOError as e:
            logging.error(f"Error saving config file: {e}")

    def restore_defaults(self):
        self.config.read_dict(DEFAULT_CONFIG)
        self.save_config()

    def get_setting(self, section, key):
        return self.config.get(section, key)

    def set_setting(self, section, key, value):
        self.config.set(section, key, value)
        self.save_config()
