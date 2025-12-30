import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "benchmark_scores": None, # If None, run on startup
    "recommended_algo": None,
    "hash_algo": "auto",
    "hash_length": 256,
    
    # Global Config
    "theme_mode": "system",
    "thread_count": "auto",
    "min_file_size": 0, # Bytes
    
    # Lists
    "ignore_folders": [],
    "ignore_extensions": [],
    "protected_files": []
}

class ConfigManager:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # Merge with defaults
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()

    def get(self, key, default=None):
        return self.config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self._save_config()

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
