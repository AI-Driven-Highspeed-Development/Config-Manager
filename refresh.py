import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

try:
    from .config_manager import ConfigManager
except ImportError:
    from config_manager import ConfigManager
cm = ConfigManager(verbose=False)