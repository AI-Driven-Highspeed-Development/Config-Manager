"""
ADHD Config Manager Package

A centralized configuration management utility for ADHD project template.
Provides singleton-based configuration management with automatic key generation.

Usage:
    from managers.config_manager import ConfigManager
    
    ## Basic usage
    cm = ConfigManager()
    value = cm.config.some_key
    
    ## With custom config file and verbose logging
    cm = ConfigManager(config_path='.custom_config', verbose=True)
    cm.save_config({'new_key': 'new_value'})
    
    ## Access raw configuration
    raw_data = cm.raw_config
"""

try:
    from .config_manager import ConfigManager
    from .config_template import ConfigTemplate
except ImportError:
    from config_manager import ConfigManager
    from config_template import ConfigTemplate

from utils.logger_util.logger import get_logger

logger = get_logger("ConfigManagerInit")
    
config_template = ConfigTemplate()

# Generate configuration
success = config_template.generate_config()
if success:
    # Show summary
    config_template.list_config_summary()
else:
    logger.error("Failed to generate configuration.")

cm = ConfigManager(verbose=False)