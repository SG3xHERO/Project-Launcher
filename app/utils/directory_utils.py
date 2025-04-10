"""
Directory utility functions for Project Launcher.
"""

import os
import logging

def ensure_directories():
    """Ensure required directories exist."""
    directories = [
        os.path.join("data"),
        os.path.join("data", "minecraft"),
        os.path.join("data", "modpacks"),
        os.path.join("data", "temp"),
        os.path.join("data", "logs"),
        os.path.join("data", "cache")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.debug(f"Ensured directory: {directory}")
    
    # Also create user home directory if needed
    os.makedirs(os.path.expanduser("~/.minecraft_launcher"), exist_ok=True)
    logging.debug("Ensured user home directory")