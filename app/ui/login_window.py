"""
Login Window UI for the Project Launcher.
"""
import hashlib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QFrame, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

class LoginWindow(QWidget):
    """Login window for Microsoft authentication."""
    
    login_success = pyqtSignal(object)
    
    def __init__(self, auth_manager, config, parent=None):
        """Initialize the login window.
        
        Args:
            auth_manager: Authentication manager.
            config: Application configuration.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Logo and welcome text
        logo_label = QLabel()
        # Add logo loading code here
        
        welcome_label = QLabel("Welcome to Project Launcher")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        
        # Login buttons layout
        buttons_layout = QVBoxLayout()
        buttons_layout.setContentsMargins(50, 10, 50, 10)
        
        # Microsoft login button
        login_btn = QPushButton("Login with Microsoft")
        login_btn.setMinimumHeight(40)
        login_btn.clicked.connect(self.start_login)
        buttons_layout.addWidget(login_btn)
        
        # Offline mode button
        offline_btn = QPushButton("Continue in Offline Mode")
        offline_btn.setMinimumHeight(40)
        offline_btn.setStyleSheet("background-color: #808080; color: white;")
        offline_btn.clicked.connect(self.start_offline_mode)
        buttons_layout.addWidget(offline_btn)
        
        # Add widgets to layout
        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)
        layout.addStretch()
        layout.addLayout(buttons_layout)
        layout.addStretch()
    
    def start_login(self):
        """Start the Microsoft authentication process."""
        try:
            # Use the start_login method we found in AuthenticationManager
            self.auth_manager.start_login()
            
            # Check if login was successful
            if self.auth_manager.is_logged_in():
                # Get user profile information
                username = self.auth_manager.get_username()
                uuid = self.auth_manager.get_uuid()
                
                # Create a profile dict to emit with the signal
                profile = {
                    "name": username,
                    "id": uuid
                }
                
                self.login_success.emit(profile)
            else:
                QMessageBox.critical(
                    self,
                    "Login Failed",
                    "Failed to log in with Microsoft. Please try again."
                )
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Login Error",
                f"An error occurred while trying to log in:\n\n{str(e)}"
            )
    
    def start_offline_mode(self):
        """Start offline mode with an optional custom username."""
        username, ok = QInputDialog.getText(
            self,
            "Offline Mode",
            "Enter your username (or leave as Player):",
            QLineEdit.EchoMode.Normal,
            "Player"
        )
        
        if ok:  # User clicked OK
            if not username:  # If username is empty
                username = "Player"
                
            # Set offline mode in auth manager
            self.auth_manager.set_offline_mode(username)
            
            # Create profile info
            profile = {
                "name": username,
                "id": "offline-" + hashlib.md5(username.encode()).hexdigest()[:16],
                "offline_mode": True
            }
            
            # Emit login success signal
            self.login_success.emit(profile)
    
    def on_login_complete(self, profile):
        """Handle login completion.
        
        Args:
            profile: User profile data or None if login failed.
        """
        if profile:
            # Emit signal with profile
            self.login_success.emit(profile)
        else:
            QMessageBox.critical(
                self,
                "Login Failed",
                "Failed to log in with Microsoft. Please try again."
            )