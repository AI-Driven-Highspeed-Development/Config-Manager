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
# import os
# import sys


# SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.dirname(SCRIPT_DIR))

try:
    from .config_manager import ConfigManager
except ImportError:
    from config_manager import ConfigManager
cm = ConfigManager(verbose=False)

# __all__ = ['ConfigManager', 'ConfigKeysGenerator']
