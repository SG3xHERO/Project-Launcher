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
    QMenu, QMenuBar, QScrollArea, QLineEdit, QApplication  # Added QApplication here
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor, QPalette

from app.core.minecraft import MinecraftInstance
from app.core.modpack import ModpackManager
from app.core.repository import RepositoryManager
from app.microsoft_auth_webengine import MicrosoftAuthManager
from app.utils.minecraft_utils import get_player_head


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


class ModernLineEdit(QLineEdit):
    """Modern styled line edit with rounded corners."""
    
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2B3142;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 15px;
            }
            QLineEdit:focus {
                background-color: #323848;
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
        
        # Install button
        self.install_btn = ModernButton("Install", True)
        self.install_btn.setFixedSize(100, 40)
        self.install_btn.clicked.connect(lambda: self.clicked.emit(self.modpack))
        layout.addWidget(self.install_btn)
        
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.modpack)
        super().mousePressEvent(event)


class LoginWindow(QWidget):
    """Login window with modern design."""
    
    login_success = pyqtSignal(str, str)  # username, session_token
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config  # Store the config reference
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        from PyQt6.QtWidgets import QLineEdit
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Project Launcher")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Login with your Minecraft account")
        subtitle_label.setStyleSheet("font-size: 16px; color: #BFC1C7;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(20)
        
        # Username
        self.username_edit = ModernLineEdit("Email or Username")
        layout.addWidget(self.username_edit)
        
        # Password
        self.password_edit = ModernLineEdit("Password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)
        
        layout.addSpacing(10)
        
        # Login button
        self.login_btn = ModernButton("Login", True)
        self.login_btn.clicked.connect(self.login)
        layout.addWidget(self.login_btn)
        
        # Microsoft login button
        self.ms_login_btn = ModernButton("Login with Microsoft")
        self.ms_login_btn.clicked.connect(self.microsoft_login)
        layout.addWidget(self.ms_login_btn)
        
        # Skip login button (for development/testing)
        self.skip_btn = ModernButton("Skip Login (Offline Mode)")
        self.skip_btn.clicked.connect(lambda: self.login_success.emit("Offline Mode", "offline"))
        layout.addWidget(self.skip_btn)
        
        # Error message
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #FF5252; font-size: 14px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        layout.addStretch(1)
        
        # Footer
        footer_label = QLabel("Created by Ben Foggon")
        footer_label.setStyleSheet("color: #8D93A0; font-size: 12px;")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer_label)
    
    def login(self):
        """Handle login button click."""
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        if not username or not password:
            self.show_error("Please enter your username and password")
            return
            
        # In a real implementation, this would authenticate with Minecraft
        # For now, just simulate a successful login
        self.login_success.emit(username, "dummy_token")
    
    def microsoft_login(self):
        """Handle Microsoft login and transition to main menu on success."""
        try:
            logging.info("Starting Microsoft login process")
            from app.auth.microsoft_auth import MicrosoftAuthManager
            
            auth_manager = MicrosoftAuthManager(config=self.config)
            
            # Show a "Logging in..." message in the error label instead of statusBar
            self.error_label.setStyleSheet("color: #4285F4; font-size: 14px;") # Blue color for info
            self.error_label.setText("Logging in with Microsoft...")
            self.error_label.setVisible(True)
            QApplication.processEvents()  # Update UI
            
            if auth_manager.authenticate():
                logging.info("Authentication successful, retrieving profile...")
                profile = auth_manager.get_minecraft_profile()
                
                if profile:
                    username = profile['name']
                    logging.info(f"Successfully logged in as {username}")
                    
                    # Store the profile data
                    self.config.set('minecraft', 'username', username)
                    self.config.set('minecraft', 'uuid', profile['id'])
                    self.config.save()
                    
                    # Emit login success signal
                    self.login_success.emit(username, "ms_token")
                    
                    return True
                else:
                    logging.error("Profile retrieval failed")
                    self.show_error("Authentication succeeded but couldn't retrieve your Minecraft profile.")
                    return False
            else:
                logging.warning("Authentication failed or was cancelled")
                self.show_error("Authentication was cancelled or failed.")
                return False
                
        except Exception as e:
            logging.error(f"Microsoft login error: {e}")
            logging.exception("Login exception details:")
            self.show_error(f"Failed to authenticate: {str(e)}")
            return False
        finally:
            # Clear the message if needed
            if self.error_label.text() == "Logging in with Microsoft...":
                self.error_label.setVisible(False)
    
    def show_error(self, message):
        """Show error message."""
        self.error_label.setText(message)
        self.error_label.setVisible(True)


class ModpackListWindow(QWidget):
    """Modpack list window with modern design."""
    
    modpack_selected = pyqtSignal(object)
    logout = pyqtSignal()
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.repository_manager = RepositoryManager(config)
        self.modpack_manager = ModpackManager(config)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Available Modpacks")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch(1)
        
        # Username and logout
        username_layout = QHBoxLayout()
        
        self.username_label = QLabel("Player2")
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
        
        # Refresh and settings buttons
        buttons_layout = QHBoxLayout()
        
        refresh_btn = ModernButton("Refresh")
        refresh_btn.clicked.connect(self.load_modpacks)
        buttons_layout.addWidget(refresh_btn)
        
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
        
    def open_settings(self):
        """Open settings dialog."""
        from app.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # Reload repository if settings changed
            url_changed = False
            enabled_repos = self.repository_manager.get_enabled_repositories()
            if enabled_repos:
                url_changed = (enabled_repos[0].url != 
                            self.config.get("server_url", "http://localhost:5000"))
            
            if url_changed:
                # Re-initialize the repository manager with the new URL
                self.repository_manager = RepositoryManager(self.config)
                # Reload modpacks
                self.load_modpacks()
                
    def set_username(self, username):
        """Set username label."""
        self.username_label.setText(username)
        
    def load_modpacks(self):
        """Load modpacks from repositories."""
        # Clear current list
        for i in reversed(range(self.modpack_list.count())):
            widget = self.modpack_list.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        self.status_label.setText("Loading modpacks...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # In a real implementation, this would be done in a background thread
        # Update repositories
        self.repository_manager.update_all_repositories()
        
        # Get modpacks
        modpacks = self.repository_manager.search_modpacks()
        
        # Add modpacks to list
        for i, modpack_info in enumerate(modpacks):
            # Create modpack object from repository data
            modpack = Modpack(
                id=modpack_info.get("id", ""),
                name=modpack_info.get("name", "Unknown"),
                version=modpack_info.get("version", "1.0"),
                mc_versions=modpack_info.get("mc_versions", []),
                author=modpack_info.get("author", "Unknown"),
                description=modpack_info.get("description", "No description available"),
                icon_path=None,  # Will be set after download
                mods=modpack_info.get("mods", [])
            )
            
            modpack_item = ModpackItem(modpack)
            modpack_item.clicked.connect(self.on_modpack_selected)
            self.modpack_list.addWidget(modpack_item)
            
            # Update progress
            progress = (i + 1) / max(len(modpacks), 1) * 100
            self.progress_bar.setValue(int(progress))
            
        self.status_label.setText(f"Found {len(modpacks)} modpacks")
        self.progress_bar.setVisible(False)
        
    def on_modpack_selected(self, modpack):
        """Handle modpack selection."""
        self.modpack_selected.emit(modpack)


class ModpackInstallWindow(QWidget):
    """Modpack installation window with modern design."""
    
    installation_complete = pyqtSignal(bool, object)  # success, modpack
    back = pyqtSignal()
    
    def __init__(self, modpack, config, parent=None):
        super().__init__(parent)
        self.modpack = modpack
        self.config = config
        self.repository_manager = RepositoryManager(config)
        self.modpack_manager = ModpackManager(config)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Back button
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8D93A0;
                border: none;
                font-size: 15px;
                text-align: left;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back.emit)
        layout.addWidget(back_btn)
        
        # Title
        title_label = QLabel(f"Installing {self.modpack.name}")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Version info
        version_label = QLabel(f"Version {self.modpack.version} for Minecraft {', '.join(self.modpack.mc_versions)}")
        version_label.setStyleSheet("font-size: 16px; color: #BFC1C7;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        layout.addSpacing(20)
        
        # Progress container
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: #2B3142;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        progress_layout.setSpacing(15)
        
        # Status icon (could be replaced with an animated spinner)
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(48, 48)
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_icon, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Status text
        self.status_label = QLabel("Preparing to install...")
        self.status_label.setStyleSheet("font-size: 18px; color: white;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        # Detailed status
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("font-size: 14px; color: #BFC1C7;")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.detail_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
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
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_frame)
        
        layout.addStretch(1)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.cancel_btn = ModernButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_installation)
        buttons_layout.addWidget(self.cancel_btn)
        
        self.launch_btn = ModernButton("Launch", True)
        self.launch_btn.setVisible(False)
        self.launch_btn.clicked.connect(self.launch_minecraft)
        buttons_layout.addWidget(self.launch_btn)
        
        layout.addLayout(buttons_layout)
        
        # Start installation process
        # In a real implementation, this would be in a background thread
        self.install_modpack()
        
    def install_modpack(self):
        """Install the modpack."""
        # In a real implementation, this would be done in a background thread
        # For now, just simulate the installation process
        self.status_label.setText("Downloading modpack...")
        self.detail_label.setText("Connecting to server...")
        
        # Simulate download progress
        for i in range(101):
            self.progress_bar.setValue(i)
            if i < 30:
                self.detail_label.setText(f"Downloading manifest... ({i}%)")
            elif i < 60:
                self.detail_label.setText(f"Downloading mods... ({i}%)")
            elif i < 90:
                self.detail_label.setText(f"Downloading resources... ({i}%)")
            else:
                self.detail_label.setText(f"Finalizing installation... ({i}%)")
                
            # In a real implementation, this would be the actual download progress
            # For now, just simulate with a delay
            if hasattr(QApplication, 'processEvents'):
                QApplication.processEvents()
            time.sleep(0.05)
            
        # Simulate successful installation
        self.status_label.setText("Installation Complete!")
        self.detail_label.setText(f"{self.modpack.name} has been successfully installed")
        self.progress_bar.setValue(100)
        
        # Show launch button
        self.launch_btn.setVisible(True)
        self.cancel_btn.setText("Close")
        
        # Signal installation complete
        self.installation_complete.emit(True, self.modpack)
        
    def cancel_installation(self):
        """Cancel or close the installation window."""
        # If installation is complete, just go back
        if self.progress_bar.value() == 100:
            self.back.emit()
            return
            
        # Otherwise, confirm cancellation
        result = QMessageBox.question(
            self,
            "Cancel Installation",
            "Are you sure you want to cancel the installation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            # In a real implementation, this would stop the download thread
            self.back.emit()
            
    def launch_minecraft(self):
        """Launch Minecraft with the installed modpack."""
        # In a real implementation, this would launch Minecraft
        QMessageBox.information(
            self,
            "Launch Minecraft",
            f"Launching Minecraft with {self.modpack.name}..."
        )
        
        # Go back to modpack list
        self.back.emit()


class MainWindow(QMainWindow):
    """Main window with stacked layout for different screens."""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.minecraft = MinecraftInstance(config)
        self.username = ""
        self.session_token = ""
        
        self.init_ui()
        self.load_style()
        self.setup_microsoft_auth()
        
    def load_style(self):
        """Load application style."""
        self.setWindowTitle("Project Launcher")
        self.setMinimumSize(800, 600)
        
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
        self.login_window = LoginWindow(self.config)
        self.login_window.login_success.connect(self.on_login_success)
        self.stacked_widget.addWidget(self.login_window)
        
        # Modpack list screen
        self.modpack_list_window = ModpackListWindow(self.config)
        self.modpack_list_window.modpack_selected.connect(self.on_modpack_selected)
        self.modpack_list_window.logout.connect(self.on_logout)
        self.stacked_widget.addWidget(self.modpack_list_window)
        
        # Initial screen is login
        self.stacked_widget.setCurrentIndex(0)
        
        main_layout.addWidget(self.stacked_widget)

        # Create user profile section
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_label.setScaledContents(True)

        self.username_label = QLabel("BaselineLogin")  # Default text
        self.username_label.setStyleSheet("font-weight: bold;")

        # Add them to your layout
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(self.avatar_label)
        profile_layout.addWidget(self.username_label)
        profile_layout.addStretch()  # Push everything to the left

        # Add to your main layout
        main_layout.addLayout(profile_layout)
        
    def on_login_success(self, username, session_token):
        """Handle successful login."""
        self.username = username
        self.session_token = session_token

        # Log the username
        logging.info(f"Username from login: {username}")

        # Update username label
        self.username_label.setText(username)

        # Try to get the player avatar
        if hasattr(self.login_window, 'ms_auth') and self.login_window.ms_auth:
            profile = self.login_window.ms_auth.get_minecraft_profile()
            if profile:
                # Log the profile data
                logging.info(f"Fetched Minecraft profile: {profile}")

                # Update username
                self.username_label.setText(profile.get('name', 'Debug4'))

                # Fetch and update avatar using get_player_head
                avatar = get_player_head(uuid=profile.get('id'))
                if avatar:
                    self.avatar_label.setPixmap(avatar)
                else:
                    # Set default avatar if no avatar is available
                    default_avatar = os.path.join("app", "ui", "resources", "default_avatar.png")
                    if os.path.exists(default_avatar):
                        self.avatar_label.setPixmap(QPixmap(default_avatar))
            else:
                logging.warning("Failed to fetch Minecraft profile.")
        else:
            logging.warning("Microsoft authentication object not found.")

        # Update username in modpack list
        self.modpack_list_window.set_username(username)

        # Load modpacks
        self.modpack_list_window.load_modpacks()

        # Switch to modpack list screen
        self.stacked_widget.setCurrentIndex(1)
        
    def on_logout(self):
        """Handle logout."""
        self.username = ""
        self.session_token = ""
        
        # Switch to login screen
        self.stacked_widget.setCurrentIndex(0)
        
    def on_modpack_selected(self, modpack):
        """Handle modpack selection."""
        # Create install window
        install_window = ModpackInstallWindow(modpack, self.config)
        install_window.installation_complete.connect(self.on_installation_complete)
        install_window.back.connect(lambda: self.stacked_widget.removeWidget(install_window))
        
        # Add to stacked widget and show
        self.stacked_widget.addWidget(install_window)
        self.stacked_widget.setCurrentWidget(install_window)
        
    def on_installation_complete(self, success, modpack):
        """Handle installation completion."""
        if success:
            # In a real implementation, this would update the modpack list
            self.modpack_list_window.load_modpacks()
            
    def setup_microsoft_auth(self):
        self.ms_auth = MicrosoftAuthManager(self.config)
        
        # Add a sign-in button to your UI
        self.ms_signin_button = QPushButton("Sign in with Microsoft")
        self.ms_signin_button.clicked.connect(self.handle_microsoft_signin)
        
        # Add the button to an appropriate layout in your UI
        # For example: self.some_layout.addWidget(self.ms_signin_button)

    def handle_microsoft_signin(self):
        """Handle Microsoft sign-in button click."""
        try:
            # Disable the button while signing in
            self.ms_signin_button.setEnabled(False)
            self.ms_signin_button.setText("Signing in...")
            
            # Try to authenticate
            if self.ms_auth.authenticate():
                profile = self.ms_auth.get_minecraft_profile()
                if profile:
                    # Update UI to show logged-in state
                    username = profile['name']
                    self.username = username
                    self.session_token = "ms_token"
                    
                    # Update the profile UI components
                    self.username_label.setText(username)
                    
                    # Set the avatar if available
                    if 'avatar' in profile and profile['avatar']:
                        self.avatar_label.setPixmap(profile['avatar'])
                    else:
                        # Fallback to default avatar
                        default_avatar = os.path.join("app", "ui", "resources", "default_avatar.png")
                        self.avatar_label.setPixmap(QPixmap(default_avatar))
                    
                    # Store user info in config
                    self.config.set("username", self.username)
                    self.config.set("auth_type", "microsoft")
                    self.config.save()
                    
                    # Show success message and proceed to main screen
                    self.on_login_success(username, "ms_token")
                else:
                    QMessageBox.warning(self, "Sign In Failed", 
                                      "Could not retrieve Minecraft profile.")
            else:
                # User may have cancelled, so don't show error message
                pass
        except Exception as e:
            logging.error(f"Microsoft authentication error: {e}")
            QMessageBox.warning(self, "Authentication Error", 
                              f"An error occurred during authentication: {str(e)}")
        finally:
            # Re-enable the button regardless of outcome
            self.ms_signin_button.setEnabled(True)
            if not self.username:
                self.ms_signin_button.setText("Sign in with Microsoft")

    def setup_minecraft_auth(self):
        self.ms_auth = MicrosoftAuthManager(self.config)
        
        self.ms_signin_button = QPushButton("Sign in with Microsoft")
        self.ms_signin_button.clicked.connect(self.handle_microsoft_signin)
        
        # Add button to your layout
        # self.some_layout.addWidget(self.ms_signin_button)

    def handle_microsoft_signin(self):
        if self.ms_auth.authenticate():
            # Check if user owns the game
            if self.ms_auth.check_game_ownership():
                profile = self.ms_auth.get_minecraft_profile()
                if profile:
                    self.ms_signin_button.setText(f"Signed in as {profile['name']}")
                    # Store profile info
                    self.config.minecraft_profile = profile
                    self.config.save()
                    QMessageBox.information(self, "Success", f"Successfully signed in as {profile['name']}")
                else:
                    QMessageBox.warning(self, "Error", "Could not retrieve Minecraft profile.")
            else:
                QMessageBox.warning(self, "Game Ownership", "This Microsoft account does not own Minecraft.")
        else:
            QMessageBox.warning(self, "Sign In Failed", "Could not sign in with Microsoft account.")

    def update_user_profile(self, user_info):
        """Update the UI with user profile information"""
        if not user_info:
            # Default/fallback display
            self.username_label.setText("Player4")
            self.avatar_label.setPixmap(QPixmap("app/ui/resources/default_avatar.png"))
            return
        
        # Set username
        username = user_info.get('username', 'Player5')
        self.username_label.setText(username)
        
        # Set avatar
        avatar = user_info.get('avatar')
        if (avatar):
            self.avatar_label.setPixmap(avatar)
        else:
            # Fallback to default avatar
            self.avatar_label.setPixmap(QPixmap("app/ui/resources/default_avatar.png"))

    def open_login_dialog(self):
        from app.ui.login_window import LoginWindow
        login_dialog = LoginWindow(config=self.config, parent=self)
        # ...rest of method...

    def show_main_menu(self):
        """Switch UI to main menu after successful login."""
        # Hide login widgets if any
        if hasattr(self, 'login_widget'):
            self.login_widget.hide()
        
        # Show main menu widgets
        self.stacked_widget.setCurrentIndex(1)  # Assuming index 1 is your main menu page
        
        # Update UI with username
        username = self.config.get('minecraft', 'username')
        if username:
            self.username_label.setText(f"Welcome, {username}")
            
        # Update any other UI elements that should change after login
        self.refresh_modpack_list()  # If you have this method
        
        logging.info("Switched to main menu view")

    def microsoft_login(self, force_new=False):
        """Handle Microsoft login with option to force new login."""
        # If force_new is True, clear cached tokens first
        if force_new:
            self._clear_token_cache()
        # Rest of the login code...


