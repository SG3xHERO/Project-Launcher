"""
Utility functions for Project Launcher.
"""
# This file makes the directory a proper Python package

# Import utility functions that are referenced in main.py
from .java_utils import is_java_installed
from .memory_utils import get_memory_info, calculate_recommended_memory

def setup_logging():
    """Configure logging for the application."""
    import logging
    import os
    
    log_dir = os.path.join(os.path.expanduser("~"), ".projectlauncher", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "launcher.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def ensure_directories():
    """Ensure required directories exist."""
    import os
    
    # Common directories needed by the application
    app_dir = os.path.join(os.path.expanduser("~"), ".projectlauncher")
    dirs = [
        app_dir,
        os.path.join(app_dir, "logs"),
        os.path.join(app_dir, "instances"),
        os.path.join(app_dir, "cache"),
        os.path.join(app_dir, "temp")
    ]
    
    # Create all directories
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)