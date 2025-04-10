"""
WebEngine utility functions for Project Launcher.
"""

import os
import sys
import logging

def setup_qt_webengine():
    """
    Set up Qt WebEngine environment.
    
    This must be called before QApplication is created.
    """
    try:
        # These environment variables need to be set before importing Qt modules
        if sys.platform.startswith('linux'):
            # Required for some Linux distros
            if "QTWEBENGINE_CHROMIUM_FLAGS" not in os.environ:
                os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"

        # Force software rendering if needed
        if "QTWEBENGINE_DISABLE_GPU" not in os.environ:
            os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"

        logging.info("Qt WebEngine environment configured")
        
    except Exception as e:
        logging.error(f"Failed to configure Qt WebEngine environment: {e}")