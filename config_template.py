import os
import json
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add path handling to work from the new nested directory structure
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.getcwd()  # Use current working directory as project root
sys.path.insert(0, project_root)

from framework.modules_control import ModulesController
from utils.logger_util.logger import Logger


class ConfigTemplate:
    """A class to manage configuration templates from modules and consolidate them into .config file."""
    
    def __init__(self, config_file_path: str = ".config"):
        """
        Initialize ConfigTemplate.
        
        Args:
            config_file_path: Path to the main config file (default: ".config")
        """
        self.config_file_path = config_file_path
        self.modules_controller = ModulesController()
        self.consolidated_config: Dict[str, Any] = {}
        self.logger = Logger(name="ConfigTemplate")
    
    def find_config_templates(self) -> Dict[str, str]:
        """
        Find all .config_template files in modules.
        
        Returns:
            Dict[str, str]: Dictionary mapping module names to their config template file paths
        """
        config_templates = {}
        all_modules = self.modules_controller.get_all_modules()
        
        self.logger.info("Scanning modules for .config_template files...")
        
        for module_path, module_info in all_modules.items():
            config_template_path = os.path.join(module_path, ".config_template")
            
            if os.path.exists(config_template_path):
                config_templates[module_info.name] = config_template_path
                self.logger.info(f"Found template in {module_info.name}: {config_template_path}")
        
        if not config_templates:
            self.logger.warning("No .config_template files found in any modules")
        else:
            self.logger.info(f"Total found: {len(config_templates)} template files")
        
        return config_templates
    
    def load_config_template(self, template_path: str) -> Dict[str, Any]:
        """
        Load configuration from a template file (JSON format).
        
        Args:
            template_path: Path to the .config_template file
            
        Returns:
            Dict[str, Any]: Configuration data from the template
        """
        try:
            with open(template_path, 'r') as file:
                content = file.read().strip()
                if not content:
                    return {}
                
                # Try to load as JSON first
                try:
                    config_data = json.loads(content)
                    return config_data if config_data is not None else {}
                except json.JSONDecodeError:
                    # If JSON fails, try to parse as simple key=value format
                    config_data = {}
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            config_data[key.strip()] = value.strip()
                    
                    return config_data if config_data else {"content": content}
                    
        except Exception as e:
            self.logger.error(f"Error loading template {template_path}: {e}")
            return {}
    
    def consolidate_configs(self) -> Dict[str, Any]:
        """
        Find all config templates and consolidate them into a single configuration.
        
        Returns:
            Dict[str, Any]: Consolidated configuration with module names as keys
        """
        self.logger.info("Consolidating configuration templates...")
        
        config_templates = self.find_config_templates()
        consolidated = {}
        
        for module_name, template_path in config_templates.items():
            self.logger.info(f"Processing {module_name}...")
            config_data = self.load_config_template(template_path)
            
            if config_data:
                consolidated[module_name] = config_data
                self.logger.info(f"Loaded {len(config_data)} configuration items")
            else:
                self.logger.warning("No configuration data found")
        
        self.consolidated_config = consolidated
        return consolidated
    
    def save_consolidated_config(self) -> bool:
        """
        Save the consolidated configuration to the main .config file as JSON.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            self.logger.info(f"Saving consolidated config to {self.config_file_path}...")
            
            # Create a backup if the file already exists
            if os.path.exists(self.config_file_path):
                backup_path = f"{self.config_file_path}.backup"
                os.rename(self.config_file_path, backup_path)
                self.logger.info(f"Created backup: {backup_path}")
            
            # Save the consolidated config as JSON (compatible with ConfigManager)
            with open(self.config_file_path, 'w') as file:
                json.dump(self.consolidated_config, file, indent=2)
            
            self.logger.info(f"Successfully saved {len(self.consolidated_config)} module configurations")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving config file: {e}")
            return False
    
    def load_existing_config(self) -> Dict[str, Any]:
        """
        Load existing configuration from .config file (JSON format).
        
        Returns:
            Dict[str, Any]: Existing configuration data
        """
        if not os.path.exists(self.config_file_path):
            return {}
        
        try:
            with open(self.config_file_path, 'r') as file:
                content = file.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON config file: {e}")
            # Try to parse as key=value format as fallback
            try:
                with open(self.config_file_path, 'r') as file:
                    content = file.read().strip()
                    config_data = {}
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            config_data[key.strip()] = value.strip()
                    return config_data
            except Exception:
                return {}
        except Exception as e:
            self.logger.warning(f"Failed to load existing config: {e}")
            return {}
    
    def merge_with_existing(self, preserve_existing: bool = True) -> Dict[str, Any]:
        """
        Merge new template configs with existing configuration.
        
        Args:
            preserve_existing: If True, preserve existing values, otherwise overwrite
            
        Returns:
            Dict[str, Any]: Merged configuration
        """
        existing_config = self.load_existing_config()
        new_config = self.consolidate_configs()
        
        if preserve_existing:
            # Merge: existing values take precedence
            merged = new_config.copy()
            for key, value in existing_config.items():
                if key in merged:
                    # If both exist, merge dictionaries or keep existing value
                    if isinstance(merged[key], dict) and isinstance(value, dict):
                        merged[key].update(value)
                    else:
                        merged[key] = value
                else:
                    merged[key] = value
        else:
            # New values take precedence
            merged = existing_config.copy()
            merged.update(new_config)
        
        self.consolidated_config = merged
        return merged
    
    def generate_config(self, preserve_existing: bool = True) -> bool:
        """
        Main method to generate/update the configuration file.
        
        Args:
            preserve_existing: Whether to preserve existing configuration values
            
        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Starting configuration template processing...")
        
        try:
            if preserve_existing and os.path.exists(self.config_file_path):
                self.logger.info("Merging with existing configuration...")
                self.merge_with_existing(preserve_existing=True)
            else:
                self.logger.info("Creating new configuration...")
                self.consolidate_configs()
            
            success = self.save_consolidated_config()
            
            if success:
                self.logger.info("Configuration processing complete!")
                self.logger.info(f"Config file: {self.config_file_path}")
                self.logger.info(f"Modules processed: {len(self.consolidated_config)}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error during config generation: {e}")
            return False
    
    def list_config_summary(self):
        """Print a summary of the consolidated configuration."""
        if not self.consolidated_config:
            self.logger.warning("No configuration data available. Run generate_config() first.")
            return
        
        self.logger.info("Configuration Summary:")
        
        for module_name, config_data in self.consolidated_config.items():
            self.logger.info(f"{module_name} ✅")

def main():
    """Main function for testing ConfigTemplate."""
    config_template = ConfigTemplate()
    
    # Generate configuration
    success = config_template.generate_config()
    
    if success:
        # Show summary
        config_template.list_config_summary()
    else:
        # Using print here is acceptable for direct script invocation, but keep consistent
        # with logging for now.
        Logger(name="ConfigTemplateMain").error("Failed to generate configuration.")


if __name__ == "__main__":
    main()