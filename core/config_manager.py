import json
import os

CONFIG_PATH = os.path.expanduser("~/.config/autostash.json")

class ConfigManager:
    def __init__(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)  # ensure ~/.config exists
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'w') as f:
                json.dump({
                    "folders": [],
                    "settings": {
                        "backup_system": False,
                        "encrypt": False,
                        "compress": False,
                        "incremental": True,
                        "schedule": {
                            "frequency": "Daily",
                            "hour": "02",
                            "minute": "00"
                        },
                        "retention_days": 30,
                        "notifications": True,
                        "log_level": "INFO"
                    }
                }, f)

    def save_folders(self, folders):
        with open(CONFIG_PATH, 'r+') as f:
            data = json.load(f)
            data["folders"] = folders
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    def get_folders(self):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)["folders"]

    def save_settings(self, settings):
        with open(CONFIG_PATH, 'r+') as f:
            data = json.load(f)
            data["settings"].update(settings)
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    def get_settings(self):
        """Get all settings from the config file"""
        try:
            if not os.path.exists(CONFIG_PATH):
                # Initialize with default settings if file doesn't exist
                default_settings = {
                    "settings": {
                        "schedule": {
                            "frequency": "Daily",
                            "hour": "02",
                            "minute": "00"
                        }
                    }
                }
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(default_settings, f, indent=4)
                return default_settings["settings"]

            with open(CONFIG_PATH, 'r') as f:
                try:
                    config = json.load(f)
                    return config.get("settings", {})
                except json.JSONDecodeError:
                    # If file is corrupted, reinitialize with defaults
                    default_settings = {
                        "settings": {
                            "schedule": {
                                "frequency": "Daily",
                                "hour": "02",
                                "minute": "00"
                            }
                        }
                    }
                    with open(CONFIG_PATH, 'w') as f:
                        json.dump(default_settings, f, indent=4)
                    return default_settings["settings"]
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
            return {}

    def export_config(self):
        """Export the entire configuration"""
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)

    def import_config(self, config_data):
        """Import configuration from a dictionary"""
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)

    def reset_config(self):
        """Reset configuration to default values"""
        with open(CONFIG_PATH, 'w') as f:
            json.dump({
                "folders": [],
                "settings": {
                    "backup_system": False,
                    "encrypt": False,
                    "compress": False,
                    "incremental": True,
                    "schedule": {
                        "frequency": "Daily",
                        "hour": "02",
                        "minute": "00"
                    },
                    "retention_days": 30,
                    "notifications": True,
                    "log_level": "INFO"
                }
            }, f, indent=4)
