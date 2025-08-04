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
        
        from managers.config_manager.config_keys import ConfigKeys
        self.config = ConfigKeys()

    @staticmethod
    def _init_nested_item(item_instance, item_data):
        """Recursively initialize nested item with data."""
        for field_name, field_value in item_data.items():
            if hasattr(item_instance, field_name):
                if isinstance(field_value, dict):
                    # Handle nested dict - create nested class instance
                    nested_class = getattr(item_instance, f'{field_name}_class', None)
                    if nested_class:
                        nested_instance = nested_class()
                        for nested_key, nested_value in field_value.items():
                            if hasattr(nested_instance, nested_key):
                                setattr(nested_instance, nested_key, nested_value)
                        setattr(item_instance, field_name, nested_instance)
                else:
                    # Handle simple field
                    setattr(item_instance, field_name, field_value)

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
        new_str += "from typing import List, Optional, Dict, Any\n"
        new_str += "from managers.config_manager.config_manager import ConfigManager\n\n"
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
        list_classes = {}  # Track classes generated for lists of dicts

        for key, value in raw_config.items():
            cleansed_value = self.value_cleanse(value)
            cleansed_type = self.type_cleanse(value)
            
            if self.late_handle(cleansed_type):
                late_handles = True
                if cleansed_type in ['dict', 'Dict']:
                    continue
                elif cleansed_type in ['list', 'List'] and self._is_list_of_dicts_with_common_keys(value):
                    # Generate a common class for list of dicts with common keys
                    item_class_name = f"{key}_item"
                    list_classes[key] = item_class_name
                    new_str += indent + f"\t{key}: Optional[List['{item_class_name}']] = None\n"
                    continue
                
            new_str += indent + f"\t{key}: Optional[{cleansed_type}] = {cleansed_value}\n"

        new_str += indent + "\tpass\n"
        
        if late_handles:
            new_str += indent + "\n"
            
            # Generate classes for lists of dicts with common keys
            for key, item_class_name in list_classes.items():
                common_structure = self._get_common_dict_structure(raw_config[key])
                new_str += f"{self._generate(item_class_name, common_structure, indent_count + 1)}\n"
            
            # Generate classes for regular dicts
            for key, value in raw_config.items():
                if isinstance(value, dict) or isinstance(value, Dict):
                    new_str += f"{self._generate(f"{key}_class", value, indent_count + 1)}\n"
                    
            new_str += indent + "\tdef __init__(self):\n"
            for key, value in raw_config.items():
                if isinstance(value, list) or isinstance(value, List):
                    if key in list_classes:
                        # For lists of dicts with common keys, create list of class instances
                        # Use unified approach for both simple and complex structures
                        new_str += indent + f"\t\tself.{key} = []\n"
                        new_str += indent + f"\t\tfor item_data in {value}:\n"
                        new_str += indent + f"\t\t\titem_instance = self.{list_classes[key]}()\n"
                        new_str += indent + f"\t\t\tConfigManager._init_nested_item(item_instance, item_data)\n"
                        new_str += indent + f"\t\t\tself.{key}.append(item_instance)\n"
                    else:
                        # For regular lists
                        new_str += indent + f"\t\tself.{key} = {value}\n"
                if isinstance(value, dict) or isinstance(value, Dict):
                    new_str += indent + f"\t\tself.{key} = self.{key}_class()\n"
            new_str += indent + "\t\tpass\n"
            
        return new_str
    
    def _is_list_of_dicts_with_common_keys(self, value: List) -> bool:
        """Check if a list contains dictionaries with common keys."""
        if not isinstance(value, list) or len(value) == 0:
            return False
        
        # Check if all items are dictionaries
        if not all(isinstance(item, dict) for item in value):
            return False
        
        # Check if there are at least 2 items and they have common keys
        if len(value) < 2:
            return len(value) == 1 and isinstance(value[0], dict)  # Single dict is also valid
        
        # Get keys from first dict
        first_keys = set(value[0].keys())
        
        # Check if all other dicts have the same keys (or subset)
        for item in value[1:]:
            if not isinstance(item, dict):
                return False
            # Allow for common subset of keys
            if not first_keys.intersection(set(item.keys())):
                return False
        
        return True
    
    def _get_common_dict_structure(self, dict_list: List[Dict]) -> Dict[str, Any]:
        """Extract the common structure from a list of dictionaries."""
        if not dict_list:
            return {}
        
        if len(dict_list) == 1:
            return dict_list[0]
        
        # Find all keys present in any dictionary
        all_keys = set()
        for item in dict_list:
            all_keys.update(item.keys())
        
        # Create a structure with sample values for each key
        common_structure = {}
        for key in all_keys:
            # Find the first non-null example of this key
            for item in dict_list:
                if key in item and item[key] is not None:
                    common_structure[key] = item[key]
                    break
            else:
                # If no non-null value found, use None
                common_structure[key] = None
        
        return common_structure
    
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