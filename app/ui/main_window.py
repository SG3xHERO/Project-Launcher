#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window UI for the Project Launcher with minecraft-launcher-lib integration.
"""

import os
import logging
import platform
import subprocess
import threading
import time
import tempfile
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QFrame,
    QSplitter, QStackedWidget, QTabWidget, QFileDialog,
    QMenu, QMenuBar, QScrollArea, QLineEdit, QApplication,
    QProgressDialog, QDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor, QPalette

# Import new components
from app.auth.microsoft_auth_lib import AuthenticationManager
from app.ui.login_window import LoginWindow
from app.core.launcher_integration import MinecraftLauncher
from app.core.modpack_loader import ModpackManager, Modpack


class ModernButton(QPushButton):
    """Modern styled button with rounded corners and hover effects."""
    
    def __init__(self, text, accent=False, parent=None):
        super().__init__(text, parent)
        self.accent = accent
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Set style based on button type
        if accent:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #E61B72;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F32A81;
                }
                QPushButton:pressed {
                    background-color: #D10A61;
                }
                QPushButton:disabled {
                    background-color: #444B5A;
                    color: #8D93A0;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2B3142;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background-color: #363D51;
                }
                QPushButton:pressed {
                    background-color: #222736;
                }
                QPushButton:disabled {
                    background-color: #232734;
                    color: #6D727E;
                }
            """)


class ModpackItem(QFrame):
    """Custom modpack list item with modern design."""
    
    clicked = pyqtSignal(object)
    
    def __init__(self, modpack, parent=None):
        super().__init__(parent)
        self.modpack = modpack
        self.setFixedHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #2B3142;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                background-color: #363D51;
            }
        """)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        
        # Try to load icon
        icon_path = modpack.icon_path
        if (icon_path and os.path.exists(icon_path)):
            pixmap = QPixmap(icon_path)
        else:
            # Use default icon
            default_icon = os.path.join("app", "ui", "resources", "modpack_icon.png")
            if os.path.exists(default_icon):
                pixmap = QPixmap(default_icon)
            else:
                # Create a colored square as fallback
                image = QImage(64, 64, QImage.Format.Format_ARGB32)
                image.fill(QColor("#E61B72"))
                pixmap = QPixmap.fromImage(image)
        
        # Apply rounded corners to icon
        icon_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setStyleSheet("""
            border-radius: 8px;
            background-color: #232734;
        """)
        
        layout.addWidget(icon_label)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(15, 0, 0, 0)
        
        name_label = QLabel(modpack.name)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        info_layout.addWidget(name_label)
        
        description_label = QLabel(modpack.description[:100] + "..." if len(modpack.description) > 100 else modpack.description)
        description_label.setStyleSheet("color: #BFC1C7; font-size: 13px;")
        description_label.setWordWrap(True)
        info_layout.addWidget(description_label)
        
        # Version info
        version_label = QLabel(f"v{modpack.version} • {', '.join(modpack.mc_versions)}")
        version_label.setStyleSheet("color: #8D93A0; font-size: 12px;")
        info_layout.addWidget(version_label)
        
        layout.addLayout(info_layout, 1)
        
        # Play/Install button
        if modpack.is_installed:
            self.action_btn = ModernButton("Play", True)
        else:
            self.action_btn = ModernButton("Install", True)
            
        self.action_btn.setFixedSize(100, 40)
        self.action_btn.clicked.connect(lambda: self.clicked.emit(self.modpack))
        layout.addWidget(self.action_btn)
        
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.modpack)
        super().mousePressEvent(event)


class ModpackListWindow(QWidget):
    """Modpack list window with modern design."""
    
    modpack_selected = pyqtSignal(object)
    logout = pyqtSignal()
    
    def __init__(self, config, auth_manager, minecraft_launcher, modpack_manager, parent=None):
        super().__init__(parent)
        self.config = config
        self.auth_manager = auth_manager
        self.minecraft_launcher = minecraft_launcher
        self.modpack_manager = modpack_manager
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Project Launcher")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch(1)
        
        # Username and logout
        username_layout = QHBoxLayout()
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(32, 32)
        self.avatar_label.setStyleSheet("border-radius: 16px; background-color: #2B3142;")
        username_layout.addWidget(self.avatar_label)
        
        self.username_label = QLabel("Player")
        self.username_label.setStyleSheet("color: #BFC1C7; font-size: 15px;")
        username_layout.addWidget(self.username_label)
        
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8D93A0;
                border: none;
                font-size: 15px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.logout.emit)
        username_layout.addWidget(logout_btn)
        
        header_layout.addLayout(username_layout)
        
        layout.addLayout(header_layout)
        
        # Modpack list header
        list_header = QHBoxLayout()
        
        modpack_list_label = QLabel("Available Modpacks")
        modpack_list_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        list_header.addWidget(modpack_list_label)
        
        list_header.addStretch(1)
        
        import_btn = QPushButton("Import Modpack")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B3142;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #363D51;
            }
        """)
        import_btn.clicked.connect(self.import_modpack)
        list_header.addWidget(import_btn)
        
        layout.addLayout(list_header)
        
        # Modpack list
        self.modpack_list = QVBoxLayout()
        self.modpack_list.setSpacing(10)
        
        # Wrap in a widget with scrolling
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.modpack_list)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #232734;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #444B5A;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5A6173;
            }
        """)
        
        layout.addWidget(scroll_area, 1)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        refresh_btn = ModernButton("Refresh")
        refresh_btn.clicked.connect(self.load_modpacks)
        buttons_layout.addWidget(refresh_btn)
        
        create_modpack_btn = ModernButton("Create Modpack")
        create_modpack_btn.clicked.connect(self.create_modpack)
        buttons_layout.addWidget(create_modpack_btn)
        
        settings_btn = ModernButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        buttons_layout.addWidget(settings_btn)
        
        layout.addLayout(buttons_layout)
        
        # Status bar
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #8D93A0; font-size: 13px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch(1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #232734;
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #E61B72;
                border-radius: 4px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(status_layout)
    
    def set_user_info(self, profile):
        """Set user information.
        
        Args:
            profile (dict): User profile information.
        """
        # Set username
        self.username_label.setText(profile.get("name", "Player"))
        
        # Try to load avatar if available
        # In a production implementation, you would fetch the avatar from Minecraft API
        # For now, we'll use a placeholder
        try:
            uuid = profile.get("id", "")
            if uuid:
                # Try to get avatar using UUID
                from app.utils.minecraft_utils import get_player_head
                avatar = get_player_head(uuid=uuid)
                if avatar:
                    self.avatar_label.setPixmap(avatar.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    self.avatar_label.setStyleSheet("border-radius: 16px;")
                    return
        except Exception as e:
            logging.warning(f"Failed to load avatar: {e}")
        
        # Use default avatar as fallback
        default_avatar = os.path.join("app", "ui", "resources", "default_avatar.png")
        if os.path.exists(default_avatar):
            self.avatar_label.setPixmap(QPixmap(default_avatar).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
    def load_modpacks(self):
        """Load modpacks from the modpack manager."""
        # Clear current list
        for i in reversed(range(self.modpack_list.count())):
            widget = self.modpack_list.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        self.status_label.setText("Loading modpacks...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Load installed modpacks
        modpacks = self.modpack_manager.get_installed_modpacks()
        
        # Add modpacks to list
        for i, modpack in enumerate(modpacks):
            modpack_item = ModpackItem(modpack)
            modpack_item.clicked.connect(self.on_modpack_selected)
            self.modpack_list.addWidget(modpack_item)
            
            # Update progress
            progress = (i + 1) / max(len(modpacks), 1) * 100
            self.progress_bar.setValue(int(progress))
        
        self.status_label.setText(f"Found {len(modpacks)} modpacks")
        self.progress_bar.setVisible(False)
        
        # If no modpacks found, add a placeholder message
        if len(modpacks) == 0:
            no_modpacks_label = QLabel("No modpacks found. Import a modpack or create a new one.")
            no_modpacks_label.setStyleSheet("color: #8D93A0; font-size: 16px; padding: 20px; background-color: #2B3142; border-radius: 8px;")
            no_modpacks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.modpack_list.addWidget(no_modpacks_label)
    
    def on_modpack_selected(self, modpack):
        """Handle modpack selection.
        
        Args:
            modpack (Modpack): Selected modpack.
        """
        if modpack.is_installed:
            # Launch modpack
            self.launch_modpack(modpack)
        else:
            # Install modpack
            self.install_modpack(modpack)
    
    def launch_modpack(self, modpack):
        """Launch a modpack.
        
        Args:
            modpack (Modpack): Modpack to launch.
        """
        try:
            # Show launching message
            self.status_label.setText(f"Launching {modpack.name}...")
            
            # Launch modpack
            process = self.modpack_manager.launch_modpack(
                modpack,
                self.auth_manager
            )
            
            # Show success message
            self.status_label.setText(f"Launched {modpack.name}")
            
            # Minimize launcher window (optional)
            main_window = self.window()
            if main_window and isinstance(main_window, QMainWindow):
                main_window.showMinimized()
                
        except Exception as e:
            logging.error(f"Failed to launch modpack: {e}")
            QMessageBox.critical(
                self,
                "Launch Error",
                f"Failed to launch {modpack.name}:\n\n{str(e)}"
            )
            self.status_label.setText("Launch failed")
    
    def install_modpack(self, modpack):
        """Install a modpack.
        
        Args:
            modpack (Modpack): Modpack to install.
        """
        self.modpack_selected.emit(modpack)
    
    def import_modpack(self):
        """Import a modpack from a ZIP file."""
        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Modpack",
            "",
            "Modpack Files (*.zip)"
        )
        
        if not file_path:
            return
        
        # Show progress dialog
        progress_dialog = QProgressDialog("Installing modpack...", "Cancel", 0, 100, self)
        progress_dialog.setWindowTitle("Installing Modpack")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        
        # Create progress callback
        def progress_callback(progress, status):
            if progress_dialog.wasCanceled():
                return
            progress_dialog.setValue(int(progress * 100))
            progress_dialog.setLabelText(status)
        
        # Install modpack in a separate thread
        class InstallThread(QThread):
            install_finished = pyqtSignal(object)
            install_failed = pyqtSignal(str)
            
            def __init__(self, modpack_manager, file_path, progress_callback):
                super().__init__()
                self.modpack_manager = modpack_manager
                self.file_path = file_path
                self.progress_callback = progress_callback
            
            def run(self):
                try:
                    modpack = self.modpack_manager.install_modpack(
                        self.file_path,
                        self.progress_callback
                    )
                    
                    if modpack:
                        self.install_finished.emit(modpack)
                    else:
                        self.install_failed.emit("Failed to install modpack")
                except Exception as e:
                    self.install_failed.emit(str(e))
        
        # Create and start thread
        install_thread = InstallThread(self.modpack_manager, file_path, progress_callback)
        install_thread.install_finished.connect(self.on_import_finished)
        install_thread.install_failed.connect(self.on_import_failed)
        install_thread.finished.connect(progress_dialog.close)
        
        # Connect cancel signal
        progress_dialog.canceled.connect(install_thread.terminate)
        
        # Start thread and show dialog
        install_thread.start()
        progress_dialog.exec()
    
    def on_import_finished(self, modpack):
        """Handle successful modpack import.
        
        Args:
            modpack (Modpack): Imported modpack.
        """
        QMessageBox.information(
            self,
            "Import Successful",
            f"Modpack {modpack.name} has been imported successfully."
        )
        
        # Refresh modpack list
        self.load_modpacks()
    
    def on_import_failed(self, error):
        """Handle failed modpack import.
        
        Args:
            error (str): Error message.
        """
        QMessageBox.critical(
            self,
            "Import Failed",
            f"Failed to import modpack:\n\n{error}"
        )
    
    def create_modpack(self):
        """Create a new modpack."""
        # In a real implementation, this would open a dialog to create a new modpack
        # For now, create a simple modpack with default values
        try:
            modpack = self.modpack_manager.create_modpack(
                name="New Modpack",
                version="1.0.0",
                mc_versions=["1.19.4"],
                author="Player",
                description="A new modpack created with Project Launcher.",
                loader_type="forge",
                loader_version="45.1.0"  # Example forge version for 1.19.4
            )
            
            if modpack:
                QMessageBox.information(
                    self,
                    "Modpack Created",
                    f"Modpack '{modpack.name}' has been created successfully."
                )
                
                # Refresh modpack list
                self.load_modpacks()
        except Exception as e:
            logging.error(f"Failed to create modpack: {e}")
            QMessageBox.critical(
                self,
                "Create Failed",
                f"Failed to create modpack:\n\n{str(e)}"
            )
    
    def open_settings(self):
        """Open settings dialog."""
        from app.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # Reload if settings changed
            pass


class MainWindow(QMainWindow):
    """Main window with stacked layout for different screens."""
    
    def __init__(self, config, auth_manager, minecraft_launcher, modpack_manager, parent=None):
        super().__init__(parent)
        self.config = config
        self.auth_manager = auth_manager
        self.minecraft_launcher = minecraft_launcher
        self.modpack_manager = modpack_manager
        
        self.init_ui()
        self.load_style()
    
    def load_style(self):
        """Load application style."""
        self.setWindowTitle("Project Launcher")
        self.setMinimumSize(900, 600)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1A1C23;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Set icon
        icon_path = os.path.join("app", "ui", "resources", "PL-logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
    
    def init_ui(self):
        """Initialize the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Stacked widget for different screens
        self.stacked_widget = QStackedWidget()
        
        # Login screen
        self.login_window = LoginWindow(self.auth_manager, self.config)
        self.login_window.login_success.connect(self.on_login_success)
        self.stacked_widget.addWidget(self.login_window)
        
        # Modpack list screen
        self.modpack_list_window = ModpackListWindow(
            self.config, 
            self.auth_manager, 
            self.minecraft_launcher,
            self.modpack_manager
        )
        self.modpack_list_window.modpack_selected.connect(self.on_modpack_selected)
        self.modpack_list_window.logout.connect(self.on_logout)
        self.stacked_widget.addWidget(self.modpack_list_window)
        
        # Initial screen is login
        self.stacked_widget.setCurrentIndex(0)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Create menu bar
        self.create_menu_bar()
    
    def create_menu_bar(self):
        """Create menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Import modpack action
        import_action = file_menu.addAction("Import Modpack")
        import_action.triggered.connect(self.import_modpack)
        
        # Settings action
        settings_action = file_menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        # About action
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
        # Check for updates action
        updates_action = help_menu.addAction("Check for Updates")
        updates_action.triggered.connect(self.check_for_updates)
    
    def on_login_success(self, profile):
        """Handle successful login.
        
        Args:
            profile (dict): User profile information.
        """
        # Update user info in modpack list
        self.modpack_list_window.set_user_info(profile)
        
        # Load modpacks
        self.modpack_list_window.load_modpacks()
        
        # Check if offline mode and update UI if needed
        if profile.get("offline_mode", False):
            self.setWindowTitle(f"Project Launcher - Offline Mode ({profile.get('name', 'Player')})")
        
        # Switch to modpack list screen
        self.stacked_widget.setCurrentIndex(1)
    
    def on_logout(self):
        """Handle logout."""
        # Log out the current user
        self.auth_manager.logout()
        
        # Switch to login screen
        self.stacked_widget.setCurrentIndex(0)
    
    def on_modpack_selected(self, modpack):
        """Handle modpack selection for installation.
        
        Args:
            modpack (Modpack): Selected modpack.
        """
        # For now, we'll just show a message
        # In a real implementation, this would create an installation window
        progress_dialog = QProgressDialog("Installing modpack...", "Cancel", 0, 100, self)
        progress_dialog.setWindowTitle(f"Installing {modpack.name}")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        
        # Create progress callback
        def progress_callback(progress, status):
            if progress_dialog.wasCanceled():
                return
            progress_dialog.setValue(int(progress * 100))
            progress_dialog.setLabelText(status)
        
        # Install modpack in a separate thread
        class InstallThread(QThread):
            install_finished = pyqtSignal(object)
            install_failed = pyqtSignal(str)
            
            def __init__(self, modpack_manager, modpack, progress_callback):
                super().__init__()
                self.modpack_manager = modpack_manager
                self.modpack = modpack
                self.progress_callback = progress_callback
            
            def run(self):
                try:
                    # Simulate installation with a temporary file
                    # In a real implementation, this would download the modpack
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
                        temp_path = temp_file.name
                    
                    # Create a basic modpack at the path
                    # In a real implementation, this would be downloaded from a repository
                    installed_modpack = self.modpack_manager.create_modpack(
                        name=self.modpack.name,
                        version=self.modpack.version,
                        mc_versions=self.modpack.mc_versions,
                        author=self.modpack.author,
                        description=self.modpack.description,
                        loader_type="forge",
                        loader_version="36.2.39",  # example forge version for 1.16.5
                    )
                    
                    if installed_modpack:
                        self.install_finished.emit(installed_modpack)
                    else:
                        self.install_failed.emit("Failed to install modpack")
                    
                    # Clean up
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                        
                except Exception as e:
                    self.install_failed.emit(str(e))
        
        # Create and start thread
        install_thread = InstallThread(self.modpack_manager, modpack, progress_callback)
        install_thread.install_finished.connect(self.on_install_finished)
        install_thread.install_failed.connect(self.on_install_failed)
        install_thread.finished.connect(progress_dialog.close)
        
        # Connect cancel signal
        progress_dialog.canceled.connect(install_thread.terminate)
        
        # Start thread and show dialog
        install_thread.start()
        progress_dialog.exec()
    
    def on_install_finished(self, modpack):
        """Handle successful modpack installation.
        
        Args:
            modpack (Modpack): Installed modpack.
        """
        QMessageBox.information(
            self,
            "Installation Successful",
            f"Modpack {modpack.name} has been installed successfully."
        )
        
        # Refresh modpack list
        self.modpack_list_window.load_modpacks()
    
    def on_install_failed(self, error):
        """Handle failed modpack installation.
        
        Args:
            error (str): Error message.
        """
        QMessageBox.critical(
            self,
            "Installation Failed",
            f"Failed to install modpack:\n\n{error}"
        )
    
    def import_modpack(self):
        """Import a modpack from a ZIP file."""
        # Only available when on modpack list screen
        if self.stacked_widget.currentIndex() == 1:
            self.modpack_list_window.import_modpack()
    
    def open_settings(self):
        """Open settings dialog."""
        from app.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # Reload if settings changed
            pass
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Project Launcher",
            "Project Launcher v1.0\n"
            "A lightweight, user-friendly Minecraft launcher with modpack management.\n\n"
            "Created by Ben Foggon\n"
            "© 2025 Project Networks"
        )
    
    def check_for_updates(self):
        """Check for updates."""
        QMessageBox.information(
            self,
            "Check for Updates",
            "No updates available."
        )
    
    def closeEvent(self, event):
        """Handle window close event.
        
        Args:
            event: Close event.
        """
        # Confirm exit if we're logged in
        if self.stacked_widget.currentIndex() == 1:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()