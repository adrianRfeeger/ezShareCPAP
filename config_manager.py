import json
import pathlib
import platform

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = pathlib.Path(config_file).expanduser()
        self.config = {}
        self.load_config()

    def load_config(self):
        if self.config_file.exists():
            try:
                with self.config_file.open('r', encoding='utf-8') as f:
                    self.config = json.load(f)
                # Ensure all default settings are included
                self.merge_default_config()
            except (json.JSONDecodeError, IOError) as e:
                import logging
                logging.error(f"Error loading config file: {e}. Loading defaults.")
                self.config = self.get_default_config()
                self.save_config()
        else:
            self.config = self.get_default_config()
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.save_config()

    def save_config(self):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with self.config_file.open('w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            import logging
            logging.error(f"Error saving config file: {e}")

    def restore_defaults(self):
        self.config = self.get_default_config()
        self.save_config()

    def get_setting(self, section, key):
        return self.config.get(section, {}).get(key)

    def set_setting(self, section, key, value):
        if section in self.config:
            self.config[section][key] = value
        else:
            self.config[section] = {key: value}
        self.save_config()

    def get_default_config(self):
        return {
            'Settings': {
                'path': '~/Documents/CPAP_Data/SD_card',
                'url': 'http://192.168.4.1/dir?dir=A:',
                'import_oscar': False,
                'quit_after_completion': False
            },
            'WiFi': {
                'ssid': 'ez Share',
                'psk': '88888888'
            },
            'Window': {
                'x': 100,
                'y': 100
            }
        }

    def merge_default_config(self):
        defaults = self.get_default_config()
        for section, values in defaults.items():
            if section not in self.config:
                self.config[section] = values
            else:
                for key, value in values.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value
        self.save_config()
