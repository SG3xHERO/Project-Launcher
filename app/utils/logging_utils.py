"""
Logging utility functions for Project Launcher.
"""

import os
import sys
import logging
import platform
import time
from logging.handlers import RotatingFileHandler

def setup_logging(log_level=logging.INFO):
    """Set up logging configuration.
    
    Args:
        log_level: Logging level.
    """
    log_dir = os.path.join("data", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"launcher_{time.strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"Logging to {log_file}")
    logging.info(f"System: {platform.system()} {platform.release()}")
    logging.info(f"Python: {platform.python_version()}")