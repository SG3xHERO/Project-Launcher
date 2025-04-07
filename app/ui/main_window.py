#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window UI for the Project Launcher.
"""

import os
import logging
import platform
import subprocess
import threading
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QFrame,
    QSplitter, QStackedWidget, QTabWidget, QFileDialog,
    QMenu, QMenuBar
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap, QAction

from app.core.minecraft import MinecraftInstance
from app.core.modpack import ModpackManager, Modpack
from app.ui.modpack_manager import ModpackManagerWidget
from app.ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Main window of the Project Launcher."""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.minecraft = MinecraftInstance(config)
        self.modpack_manager = ModpackManager(config)
        
        self.init_ui()
        self.load_style()
        self.check_minecraft_installation()
        self.load_modpacks()
        
        # Check for updates in the background
        self.check_for_updates()

    def load_style(self):
        """Load application style."""
        style_path = os.path.join("app", "ui", "resources", "style.css")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        
        # Set window properties
        self.setWindowTitle("Project Launcher")
        icon_path = os.path.join("app", "ui", "resources", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Project Launcher")
        self.setMinimumSize(900, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Menu bar
        self.create_menu_bar()
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #2D2D44; color: white; border-radius: 5px;")
        header_layout = QHBoxLayout(header_frame)
        
        # Logo/Title
        title_label = QLabel("Project Launcher")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        # Version selector
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(150)
        self.version_combo.currentIndexChanged.connect(self.on_version_changed)
        header_layout.addWidget(QLabel("Minecraft Version:"))
        header_layout.addWidget(self.version_combo)
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)
        
        main_layout.addWidget(header_frame)
        
        # Content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Modpack list
        modpack_frame = QFrame()
        modpack_frame.setFrameShape(QFrame.Shape.StyledPanel)
        modpack_layout = QVBoxLayout(modpack_frame)
        
        modpack_header = QLabel("Installed Modpacks")
        modpack_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        modpack_layout.addWidget(modpack_header)
        
        self.modpack_list = QListWidget()
        self.modpack_list.setIconSize(QSize(48, 48))
        self.modpack_list.currentItemChanged.connect(self.on_modpack_selected)
        modpack_layout.addWidget(self.modpack_list)
        
        modpack_buttons_layout = QHBoxLayout()
        
        add_modpack_btn = QPushButton("Install Modpack")
        add_modpack_btn.clicked.connect(self.install_modpack)
        modpack_buttons_layout.addWidget(add_modpack_btn)
        
        create_modpack_btn = QPushButton("Create Modpack")
        create_modpack_btn.clicked.connect(self.create_modpack)
        modpack_buttons_layout.addWidget(create_modpack_btn)
        
        modpack_layout.addLayout(modpack_buttons_layout)
        
        # Modpack details
        details_frame = QFrame()
        details_frame.setFrameShape(QFrame.Shape.StyledPanel)
        details_layout = QVBoxLayout(details_frame)
        
        self.modpack_detail_widget = ModpackManagerWidget(self.config, self.modpack_manager)
        details_layout.addWidget(self.modpack_detail_widget)
        
        # Add to splitter
        content_splitter.addWidget(modpack_frame)
        content_splitter.addWidget(details_frame)
        content_splitter.setSizes([300, 600])
        
        main_layout.addWidget(content_splitter, 1)
        
        # Launch button area
        launch_frame = QFrame()
        launch_frame.setStyleSheet("background-color: #2D2D44; border-radius: 5px;")
        launch_layout = QHBoxLayout(launch_frame)
        
        self.launch_btn = QPushButton("LAUNCH MINECRAFT")
        self.launch_btn.setObjectName("launchButton")
        self.launch_btn.setMinimumHeight(50)
        self.launch_btn.clicked.connect(self.launch_minecraft)
        launch_layout.addWidget(self.launch_btn)
        
        main_layout.addWidget(launch_frame)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("Ready")

    def create_menu_bar(self):
        """Create menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        settings_action = file_menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        install_manager_action = tools_menu.addAction("Installation Manager")
        install_manager_action.triggered.connect(self.open_install_manager)
        
        tools_menu.addSeparator()
        
        java_menu = tools_menu.addMenu("Java")
        
        install_java_action = java_menu.addAction("Install Java 21")
        install_java_action.triggered.connect(self.install_java)
        
        detect_java_action = java_menu.addAction("Detect Java")
        detect_java_action.triggered.connect(self.detect_java)
        
        minecraft_menu = tools_menu.addMenu("Minecraft")
        
        install_minecraft_action = minecraft_menu.addAction("Install Minecraft")
        install_minecraft_action.triggered.connect(self.install_minecraft)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
        check_updates_action = help_menu.addAction("Check for Updates")
        check_updates_action.triggered.connect(self.check_for_updates)

    def check_minecraft_installation(self):
        """Check if Minecraft is installed and load available versions."""
        from app.core.minecraft_downloader import MinecraftDownloader
        
        # Create Minecraft downloader
        mc_downloader = MinecraftDownloader(self.config)
        
        # Get installed versions
        installed_versions = mc_downloader.get_installed_versions()
        
        # Clear combo box
        self.version_combo.clear()
        
        # Add installed versions
        for version in installed_versions:
            self.version_combo.addItem(version, version)
            
        # If no versions installed, add some common ones
        if not installed_versions:
            common_versions = ["1.20.2", "1.19.4", "1.18.2", "1.16.5"]
            for version in common_versions:
                self.version_combo.addItem(f"{version} (Not Installed)", version)
                
        # Set to default or last used version
        default_version = self.config.get("minecraft_version", "1.19.4")
        
        # Try to find the version
        for i in range(self.version_combo.count()):
            if self.version_combo.itemData(i) == default_version:
                self.version_combo.setCurrentIndex(i)
                break

    def load_modpacks(self):
        """Load installed modpacks into the list."""
        self.modpack_list.clear()
        
        modpacks = self.modpack_manager.get_installed_modpacks()
        for modpack in modpacks:
            item = QListWidgetItem(modpack.name)
            # In a real implementation, try to load actual modpack icons
            icon_path = modpack.icon_path
            if icon_path and os.path.exists(icon_path):
                item.setIcon(QIcon(icon_path))
            else:
                # Use default icon
                default_icon = os.path.join("app", "ui", "resources", "icon.png")
                if os.path.exists(default_icon):
                    item.setIcon(QIcon(default_icon))
                    
            item.setData(Qt.ItemDataRole.UserRole, modpack)
            self.modpack_list.addItem(item)

    def on_version_changed(self, index):
        """Handle Minecraft version change."""
        if index < 0:
            return
            
        version = self.version_combo.currentData()
        if not version:
            return
            
        logging.info(f"Minecraft version changed to {version}")
        self.config.set("minecraft_version", version)
        self.config.save()
        
        # Check if selected version is installed
        version_text = self.version_combo.currentText()
        if "(Not Installed)" in version_text:
            result = QMessageBox.question(
                self,
                "Minecraft Not Installed",
                f"Minecraft {version} is not installed. Do you want to install it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                self.install_minecraft()
        
        # Update modpack compatibility
        self.modpack_detail_widget.refresh_compatibility()

    def on_modpack_selected(self, current, previous):
        """Handle modpack selection change."""
        if not current:
            self.modpack_detail_widget.clear_modpack()
            return
            
        modpack = current.data(Qt.ItemDataRole.UserRole)
        self.modpack_detail_widget.set_modpack(modpack)

    def install_modpack(self):
        """Open the modpack installation dialog."""
        from app.core.repository import RepositoryManager
        from app.ui.modpack_browser import ModpackBrowserDialog
        
        # Create repository manager
        repo_manager = RepositoryManager(self.config)
        
        # Create modpack browser dialog
        browser_dialog = ModpackBrowserDialog(
            self.config,
            repo_manager,
            self.modpack_manager,
            self
        )
        
        # Connect signals
        browser_dialog.modpack_installed.connect(self.on_modpack_installed)
        
        # Show dialog
        if browser_dialog.exec():
            # Dialog was accepted (modpack installed)
            self.load_modpacks()
            
    def on_modpack_installed(self, modpack):
        """Handle modpack installation.
        
        Args:
            modpack (Modpack): Installed modpack.
        """
        # Update UI
        self.load_modpacks()
        
        # Select the newly installed modpack
        for i in range(self.modpack_list.count()):
            item = self.modpack_list.item(i)
            item_modpack = item.data(Qt.ItemDataRole.UserRole)
            
            if item_modpack.id == modpack.id:
                self.modpack_list.setCurrentItem(item)
                break

    def create_modpack(self):
        """Open the modpack creation dialog."""
        # Check if Minecraft is installed
        mc_version = self.version_combo.currentData()
        if not mc_version:
            QMessageBox.warning(
                self,
                "No Minecraft Version",
                "Please select a Minecraft version before creating a modpack."
            )
            return
            
        # In a real implementation, this would open a dialog to
        # create a modpack with name, version, etc.
        from PyQt6.QtWidgets import QInputDialog, QLineEdit
        
        name, ok1 = QInputDialog.getText(
            self,
            "Create Modpack",
            "Enter modpack name:",
            QLineEdit.EchoMode.Normal,
            "My Custom Modpack"
        )
        
        if ok1 and name:
            # Ask for author
            author, ok2 = QInputDialog.getText(
                self,
                "Create Modpack",
                "Enter author name:",
                QLineEdit.EchoMode.Normal,
                "Ben Foggon"
            )
            
            if ok2 and author:
                # Create modpack
                try:
                    modpack = self.modpack_manager.create_modpack(
                        name=name,
                        version="1.0.0",
                        mc_versions=[mc_version],
                        author=author,
                        description=f"Custom modpack created with Project Launcher"
                    )
                    
                    if modpack:
                        QMessageBox.information(
                            self,
                            "Modpack Created",
                            f"Modpack '{name}' has been created successfully."
                        )
                        
                        # Refresh modpack list
                        self.load_modpacks()
                        
                        # Select the newly created modpack
                        for i in range(self.modpack_list.count()):
                            item = self.modpack_list.item(i)
                            item_modpack = item.data(Qt.ItemDataRole.UserRole)
                            
                            if item_modpack.id == modpack.id:
                                self.modpack_list.setCurrentItem(item)
                                break
                                
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to create modpack: {str(e)}"
                    )

    def open_settings(self):
        """Open the settings dialog."""
        settings_dialog = SettingsDialog(self.config, self)
        if settings_dialog.exec():
            # Settings were changed and saved
            self.check_minecraft_installation()
            self.load_modpacks()

    def launch_minecraft(self):
        """Launch Minecraft with the selected modpack."""
        current_item = self.modpack_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, 
                "No Modpack Selected", 
                "Please select a modpack to launch."
            )
            return
            
        modpack = current_item.data(Qt.ItemDataRole.UserRole)
        version = self.version_combo.currentData()
        
        if not version:
            QMessageBox.warning(
                self,
                "No Minecraft Version",
                "Please select a Minecraft version."
            )
            return
            
        # Check if version is installed
        version_text = self.version_combo.currentText()
        if "(Not Installed)" in version_text:
            result = QMessageBox.question(
                self,
                "Minecraft Not Installed",
                f"Minecraft {version} is not installed. Do you want to install it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                self.install_minecraft()
                return
            else:
                return
                
        # Check Java before launching
        java_path = self.config.get("java_path", "java")
        java_version = None
        
        try:
            # Run java -version to check if Java is available
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                # Extract Java version from output
                output = result.stderr
                import re
                version_match = re.search(r'version "([^"]+)"', output)
                if version_match:
                    java_version = version_match.group(1)
            else:
                raise Exception("Java not found")
        except Exception:
            # Java not found or error running java -version
            result = QMessageBox.question(
                self,
                "Java Not Found",
                "Java is required to run Minecraft. Do you want to install Java 21?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                self.install_java()
                return
            else:
                return
        
        # Launch Minecraft
        self.status_bar.showMessage(f"Launching Minecraft {version} with {modpack.name}...")
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Disable UI during launch
        self.setEnabled(False)
        
        # Start a thread to handle the launch process
        launch_thread = threading.Thread(
            target=self._launch_minecraft_thread,
            args=(modpack, version),
            daemon=True
        )
        launch_thread.start()
        
    def _launch_minecraft_thread(self, modpack, version):
        """Thread function to launch Minecraft.
        
        Args:
            modpack (Modpack): Modpack to launch.
            version (str): Minecraft version.
        """
        try:
            # Update progress
            for i in range(0, 101, 10):
                # Update progress (must be done via signals/slots for thread safety)
                self.progress_update.emit(i)
                time.sleep(0.1)
                
            # Launch Minecraft
            process = self.minecraft.launch(
                version=version,
                modpack_dir=modpack.install_path,
                callback=self._minecraft_log_callback
            )
            
            # Launch complete
            self.launch_complete.emit(True, "")
            
        except Exception as e:
            logging.error(f"Failed to launch Minecraft: {e}")
            self.launch_complete.emit(False, str(e))
            
    # Define signals for thread communication
    progress_update = pyqtSignal(int)
    launch_complete = pyqtSignal(bool, str)
    
    @pyqtSlot(int)
    def on_progress_update(self, progress):
        """Handle progress update from launch thread.
        
        Args:
            progress (int): Progress value (0-100).
        """
        self.progress_bar.setValue(progress)
        
    @pyqtSlot(bool, str)
    def on_launch_complete(self, success, error_message):
        """Handle launch completion.
        
        Args:
            success (bool): Whether launch was successful.
            error_message (str): Error message if launch failed.
        """
        # Re-enable UI
        self.setEnabled(True)
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_bar.showMessage("Minecraft launched successfully")
        else:
            self.status_bar.showMessage("Failed to launch Minecraft")
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Failed to launch Minecraft: {error_message}"
            )
            
    def _minecraft_log_callback(self, line):
        """Callback for Minecraft log output.
        
        Args:
            line (str): Log line from Minecraft.
        """
        # In a real implementation, this would process or display Minecraft log output
        logging.debug(f"Minecraft: {line}")

    def check_for_updates(self):
        """Check for updates to the launcher and modpacks."""
        # In a real implementation, this would check for updates in a background thread
        self.status_bar.showMessage("Checking for updates...")
        
        # Simulate checking process
        import time
        time.sleep(1)
        
        self.status_bar.showMessage("Ready")
        
    def open_install_manager(self):
        """Open the installation manager dialog."""
        from app.ui.install_dialog import InstallDialog
        
        dialog = InstallDialog(self.config, self)
        dialog.installation_complete.connect(self.on_installation_complete)
        dialog.exec()
        
    def install_java(self):
        """Install Java 21."""
        from app.core.java_installer import JavaInstaller
        from app.ui.install_dialog import JavaInstallThread
        from PyQt6.QtWidgets import QProgressDialog, QMessageBox
        
        # Create progress dialog
        progress = QProgressDialog("Preparing to install Java 21...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Installing Java")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setValue(0)
        
        # Create installer
        java_installer = JavaInstaller(self.config)
        
        # Create thread
        install_thread = JavaInstallThread(java_installer)
        
        # Connect signals
        install_thread.progress.connect(
            lambda value, status: progress.setValue(int(value * 100)) or progress.setLabelText(status)
        )
        install_thread.finished.connect(lambda success, result: self.on_java_install_finished(success, result, progress))
        
        # Start thread
        install_thread.start()
        progress.exec()
        
    def on_java_install_finished(self, success, result, progress_dialog):
        """Handle Java installation completion.
        
        Args:
            success (bool): Whether installation was successful.
            result: Installation result.
            progress_dialog: Progress dialog.
        """
        from PyQt6.QtWidgets import QMessageBox
        
        # Close progress dialog
        progress_dialog.close()
        
        if success:
            if isinstance(result, dict) and result.get("needs_manual_install"):
                # Manual installation required
                QMessageBox.information(
                    self,
                    "Manual Installation Required",
                    "The Java installer has been downloaded. Please run it manually to complete installation."
                )
            else:
                QMessageBox.information(
                    self,
                    "Java Installation Complete",
                    "Java 21 has been installed successfully and set as the current Java."
                )
                
            # Check Minecraft installation
            self.check_minecraft_installation()
        else:
            QMessageBox.warning(
                self,
                "Java Installation Failed",
                f"Failed to install Java 21: {result if isinstance(result, str) else 'Unknown error'}"
            )
            
    def detect_java(self):
        """Detect Java installations."""
        from app.core.java_installer import JavaInstaller
        from PyQt6.QtWidgets import QMessageBox
        
        java_installer = JavaInstaller(self.config)
        java_versions = java_installer.get_installed_java_versions()
        
        if java_versions:
            # Select newest Java
            newest_java = java_versions[0]  # List is sorted by version
            self.config.set("java_path", newest_java.get("path"))
            self.config.save()
            
            QMessageBox.information(
                self,
                "Java Detected",
                f"Found {len(java_versions)} Java installation(s). Using {newest_java.get('vendor')} {newest_java.get('version')}."
            )
        else:
            QMessageBox.warning(
                self,
                "No Java Found",
                "No Java installation was found. Please install Java."
            )
            
    def install_minecraft(self):
        """Install Minecraft."""
        from app.core.minecraft_downloader import MinecraftDownloader
        from app.ui.install_dialog import InstallDialog
        
        dialog = InstallDialog(self.config, self)
        dialog.tab_widget.setCurrentIndex(1)  # Switch to Minecraft tab
        dialog.installation_complete.connect(self.on_installation_complete)
        dialog.exec()
        
    def on_installation_complete(self):
        """Handle installation completion."""
        # Check Minecraft installation
        self.check_minecraft_installation()
        # Reload modpacks
        self.load_modpacks()
        
    def show_about(self):
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox
        
        QMessageBox.about(
            self,
            "About Project Launcher",
            "Project Launcher\n\n"
            "A lightweight, user-friendly Minecraft launcher with modpack management.\n\n"
            "Created by Ben Foggon"
        )