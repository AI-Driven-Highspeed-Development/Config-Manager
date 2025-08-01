import json
import os
import logging
import sys
from typing import Any, Dict, List

# Add path handling to work from the new nested directory structure
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.getcwd()  # Use current working directory as project root
sys.path.insert(0, project_root)

from utils.logger_util.logger import get_logger

# Run this file once to generate config keys
# Run this file again if you changed the .config file

class ConfigManager:
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of ConfigManager exists."""
        if not hasattr(cls, 'instance'):
            cls.instance = super(ConfigManager, cls).__new__(cls)
        return cls.instance

    def __init__(self, config_path: str = '.config', verbose: bool = False):
    
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Use centralized logger instead of internal setup
        self.logger = get_logger("ConfigManager", verbose=verbose)
        self.config_path = config_path
        self.verbose = verbose
        
        self.logger.debug("Initializing ConfigManager...")
        if not os.path.exists(self.config_path):
            self.logger.debug("Configuration file not found, creating a new one.")
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as file:
                file.write('{}')
                    
        self.raw_config = {}           
        self._load_config(self.config_path)
        self.ckg = ConfigKeysGenerator(self.raw_config)
        self.ckg.generate()
        
        # Import config keys with flexible path handling for new structure
        try:
            from managers.config_manager.config_keys import ConfigKeys
        except ImportError:
            try:
                from config_manager.config_keys import ConfigKeys
            except ImportError:
                from config_keys import ConfigKeys
        
        self.config = ConfigKeys()

    def _load_config(self, config_path):
        """Load configuration from a file."""
        try:
            with open(config_path, 'r') as file:
                config_str = file.read()
                if not config_str.strip():
                    self.logger.debug("Configuration file is empty, initializing with an empty config.")
                self.raw_config = json.loads(config_str) if config_str else {}
            self.logger.debug("Configuration loaded successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred while loading the configuration: {e}")
        
    def save_config(self, key_value: Dict[str, Any] = None):
        """Save the current configuration to a file."""
        if key_value:
            self.raw_config.update(key_value)
        try:
            with open(self.config_path, 'w') as file:
                json.dump(self.raw_config, file, indent=2)
            self.logger.debug("Configuration saved successfully.")
            self.ckg.generate()  # Regenerate config keys after saving
        except Exception as e:
            self.logger.error(f"An error occurred while saving the configuration: {e}")

        
class ConfigKeysGenerator:
    """Generates configuration keys from the current raw configuration."""
    
    def __init__(self, raw_config: Dict[str, Any] = None):
        self.raw_config = raw_config
        
    def generate(self):
        """Generate configuration keys from a predefined source."""

        new_str = f"from dataclasses import dataclass\n"
        new_str += "from typing import List, Optional, Dict, Any\n\n"
        new_str += self._generate("ConfigKeys", self.raw_config)

        # Save config_keys.py in the same directory as this file
        config_keys_path = os.path.join(current_dir, 'config_keys.py')
        os.makedirs(os.path.dirname(config_keys_path), exist_ok=True)
        
        with open(config_keys_path, 'w') as file:
            file.write(new_str)

    def _generate(self, class_name: str = None, raw_config: Dict[str, Any] = None, indent_count: int = 0):
        """Generate configuration keys from the current raw configuration."""
        indent = "\t" * indent_count
        new_str = indent + f"@dataclass\n"
        new_str += indent + f"class {class_name}:\n"
        late_handles = False

        for key, value in raw_config.items():
            cleansed_value = self.value_cleanse(value)
            cleansed_type = self.type_cleanse(value)
            
            if self.late_handle(cleansed_type):
                late_handles = True
                if cleansed_type in ['dict', 'Dict']:
                    continue
                
            new_str += indent + f"\t{key}: Optional[{cleansed_type}] = {cleansed_value}\n"

        new_str += indent + "\tpass\n"
        
        if late_handles:
            new_str += indent + "\n"
            for key, value in raw_config.items():
                if isinstance(value, dict) or isinstance(value, Dict):
                    new_str += f"{self._generate(f"{key}_class", value, indent_count + 1)}\n"
                    
            new_str += indent + "\tdef __init__(self):\n"
            for key, value in raw_config.items():
                if isinstance(value, list) or isinstance(value, List):
                    new_str += indent + f"\t\tself.{key} = {value}\n"
                if isinstance(value, dict) or isinstance(value, Dict):
                    new_str += indent + f"\t\tself.{key} = self.{key}_class()\n"
            new_str += indent + "\t\tpass\n"
            
        return new_str
    
    def late_handle(self, type: str) -> bool:
        if type in ['list', 'List', 'dict', 'Dict']:
            return True
        return False

    def type_cleanse(self, key: str) -> str:
        """Cleanses the type of a value for configuration keys."""
        if isinstance(key, list):
            return "List"
        elif isinstance(key, dict):
            return "Dict"
        else:
            return type(key).__name__
        
    def value_cleanse(self, value: Any) -> str:
        """Cleanses the value of a configuration key."""
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, List) or isinstance(value, list):
            return "None"
        else:
            return str(value)

if __name__ == "__main__":
    cm = ConfigManager(verbose=False)
    print("ConfigManager instance created successfully!")
    
    # Print some basic info
    if hasattr(cm, 'raw_config'):
        print(f"Loaded config keys: {list(cm.raw_config.keys())}")