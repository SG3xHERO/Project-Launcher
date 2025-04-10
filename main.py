#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project Launcher Launcher
A lightweight, user-friendly Project Launcher with modpack management capabilities.
"""

import sys
import os

# Add the current directory to Python path to fix import issues
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import subprocess
# Import from the new location
from app.utils.webengine_utils import setup_qt_webengine
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings, QDir, QSize
from PyQt6.QtGui import QIcon
from app.ui.main_window import MainWindow
from app.config import Config
from app.utils import setup_logging, ensure_directories

# Handle Windows-specific taskbar icon setup BEFORE QApplication is created
if sys.platform == "win32":
    try:
        import ctypes
        
        # Use consistent naming throughout application
        app_name = "Project Launcher"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_name)
        logging.info(f"Set Windows AppUserModelID to: {app_name}")
            
    except ImportError:
        logging.warning("Could not import ctypes, Windows-specific taskbar icon might not work")
    except Exception as e:
        logging.warning(f"Failed to set application ID for Windows taskbar: {e}")


def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logging.info("Starting Project Launcher...")

    # Call setup function BEFORE creating QApplication
    setup_qt_webengine()

    # Create QApplication instance - ONLY ONCE
    app = QApplication(sys.argv)
    # Make sure this EXACTLY matches the AppUserModelID from earlier
    app.setApplicationName("Project Launcher")
    app.setOrganizationName("Project Networks")
    app.setOrganizationDomain("projectnetworks.co.uk")
   
    # Set application style
    app.setStyle("Fusion")
    
    # Try to use .ico file first (better for Windows)
    icon_path_ico = os.path.abspath(os.path.join("app", "ui", "resources", "PL-logo.ico"))
    icon_path_png = os.path.abspath(os.path.join("app", "ui", "resources", "PL-logo.png"))
    
    # Select the icon path
    if os.path.exists(icon_path_ico):
        icon_path = icon_path_ico
        logging.info(f"Using ICO icon: {icon_path}")
    elif os.path.exists(icon_path_png):
        icon_path = icon_path_png
        logging.info(f"Using PNG icon: {icon_path}")
    else:
        icon_path = None
        logging.warning("No icon file found")
    
    # Apply the icon if found - ensure this happens BEFORE creating the main window
    if icon_path:
        app_icon = QIcon()
        # Add the icon file for different sizes individually
        for size in [16, 32, 48, 64, 128, 256]:
            app_icon.addFile(icon_path, QSize(size, size))
        app.setWindowIcon(app_icon)
    
    # Ensure required directories exist
    ensure_directories()

    # Load configuration
    config = Config()
    if not config.load():
        logging.info("No configuration found. Creating default configuration.")
        config.create_default()
        config.save()

    # Create main window
    main_window = MainWindow(config)
    
    # Also set icon explicitly on main window
    if icon_path:
        window_icon = QIcon()
        # Add the icon file for different sizes individually
        for size in [16, 32, 48, 64, 128, 256]:
            window_icon.addFile(icon_path, QSize(size, size))
        main_window.setWindowIcon(window_icon)
    
    # Make sure window title EXACTLY matches the AppUserModelID for Windows taskbar grouping
    if sys.platform == "win32":
        main_window.setWindowTitle("Project Launcher")  # Match exactly with AppUserModelID
    
    # Show the window
    main_window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()