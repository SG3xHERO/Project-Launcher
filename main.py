#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minecraft Modpack Launcher
A lightweight, user-friendly Minecraft launcher with modpack management capabilities.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

from app.ui.main_window import MainWindow
from app.config import Config
from app.utils import setup_logging, ensure_directories


def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logging.info("Starting Minecraft Modpack Launcher...")

    # Ensure required directories exist
    ensure_directories()

    # Load configuration
    config = Config()
    if not config.load():
        logging.info("No configuration found. Creating default configuration.")
        config.create_default()
        config.save()

    # Create QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName("Minecraft Modpack Launcher")
    app.setOrganizationName("YourOrganization")
    app.setOrganizationDomain("yourorganization.com")

    # Create and show main window
    main_window = MainWindow(config)
    main_window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()