"""
ADHD Config Manager Package

A centralized configuration management utility for ADHD project template.
Provides singleton-based configuration management with automatic key generation.

Usage:
    from config_manager import ConfigManager
    
    ## Basic usage
    cm = ConfigManager()
    value = cm.config.some_key
    
    ## With custom config file and verbose logging
    cm = ConfigManager(config_path='.custom_config', verbose=True)
    cm.save_config({'new_key': 'new_value'})
    
    ## Access raw configuration
    raw_data = cm.raw_config
"""

from .config_manager import ConfigManager
from .config_template import ConfigTemplate

__all__ = ["ConfigManager", "ConfigTemplate"]