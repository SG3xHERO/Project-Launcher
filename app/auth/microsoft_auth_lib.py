#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Microsoft Authentication Manager using minecraft-launcher-lib for Project Launcher.
"""

import os
import json
import logging
import threading
import webbrowser
import minecraft_launcher_lib
import hashlib
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, 
    QDialogButtonBox, QMessageBox, QApplication, QInputDialog, QLineEdit
)


class AuthenticationManager(QObject):
    """
    Authentication manager for Minecraft using minecraft-launcher-lib.
    """
    
    # Signals for authentication events
    auth_started = pyqtSignal()
    auth_progress = pyqtSignal(str)
    auth_success = pyqtSignal(dict)
    auth_error = pyqtSignal(str)
    
    def __init__(self, config):
        """Initialize the authentication manager.
        
        Args:
            config: Application configuration instance
        """
        super().__init__()
        self.config = config
        
        # Get Microsoft auth settings from config
        auth_config = config.get("microsoft_auth", {})
        self.client_id = auth_config.get("client_id")
        self.redirect_uri = auth_config.get("redirect_uri")
        
        # Cache file for auth data
        self.auth_cache_file = os.path.join(
            getattr(config, 'app_data_dir', '.'), 
            "auth_cache.json"
        )
        
        # Authentication data
        self.auth_data = self._load_cached_auth()
    
    def _load_cached_auth(self) -> Optional[Dict[str, Any]]:
        """Load cached authentication data if available.
        
        Returns:
            Optional[Dict[str, Any]]: Authentication data or None if not available
        """
        try:
            if os.path.exists(self.auth_cache_file):
                with open(self.auth_cache_file, 'r') as f:
                    data = json.load(f)
                logging.info("Loaded cached authentication data")
                return data
        except Exception as e:
            logging.error(f"Failed to load authentication cache: {e}")
        return None
    
    def load_cached_auth(self):
        """Load authentication data from cache file."""
        try:
            if os.path.exists(self.auth_cache_file):
                with open(self.auth_cache_file, "r") as f:
                    self.auth_data = json.load(f)
                    return True
        except Exception as e:
            logging.error(f"Failed to load cached authentication data: {e}")
        
        return False
    
    def _save_auth_cache(self, auth_data: Dict[str, Any]):
        """Save authentication data to cache file.
        
        Args:
            auth_data (Dict[str, Any]): Authentication data to save
        """
        try:
            os.makedirs(os.path.dirname(self.auth_cache_file), exist_ok=True)
            with open(self.auth_cache_file, 'w') as f:
                json.dump(auth_data, f)
            logging.info("Saved authentication data to cache")
        except Exception as e:
            logging.error(f"Failed to save authentication cache: {e}")
    
    def _save_auth_data(self):
        """Save authentication data to cache file."""
        if not self.auth_data:
            return
            
        try:
            with open(self.auth_cache_file, "w") as f:
                json.dump(self.auth_data, f)
        except Exception as e:
            logging.error(f"Failed to save authentication data: {e}")
    
    def is_logged_in(self) -> bool:
        """Check if the user is currently logged in.
        
        Returns:
            bool: True if the user is logged in, False otherwise
        """
        if not self.auth_data:
            return False
        
        # Validate the auth data
        try:
            # Check if the auth data has the necessary fields
            if not all(key in self.auth_data for key in ["access_token", "refresh_token"]):
                return False
            
            # Check if the access token is still valid
            # This is a basic check - a more thorough check would validate with the server
            return bool(self.auth_data.get("access_token"))
        except Exception:
            return False
    
    def get_username(self) -> Optional[str]:
        """Get the username of the logged-in user.
        
        Returns:
            Optional[str]: Username or None if not logged in
        """
        if not self.auth_data:
            return None
        
        return self.auth_data.get("name")
    
    def get_uuid(self) -> Optional[str]:
        """Get the UUID of the logged-in user.
        
        Returns:
            Optional[str]: UUID or None if not logged in
        """
        if not self.auth_data:
            return None
        
        return self.auth_data.get("id")
    
    def launch_minecraft(self, minecraft_directory: str, version_id: str, 
                         options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Launch Minecraft with the authenticated account.
        
        Args:
            minecraft_directory (str): Path to Minecraft directory
            version_id (str): Minecraft version ID
            options (Optional[Dict[str, Any]]): Additional launch options
            
        Returns:
            Dict[str, Any]: Minecraft launch command
        """
        if not self.is_logged_in():
            raise ValueError("User is not logged in")
        
        # Default options
        launch_options = {
            "username": self.auth_data.get("name", "Player"),
            "uuid": self.auth_data.get("id", ""),
            "token": self.auth_data.get("access_token", "")
        }
        
        # Add user-provided options
        if options:
            launch_options.update(options)
        
        # Generate command
        command = minecraft_launcher_lib.command.get_minecraft_command(
            version=version_id,
            minecraft_directory=minecraft_directory,
            options=launch_options
        )
        
        logging.info(f"Generated Minecraft launch command for version {version_id}")
        return command
    
    def start_login(self):
        """Start the Microsoft authentication process using device code flow."""
        try:
            import requests
            import time
            
            # Emit started signal
            self.auth_started.emit()
            
            # Create a custom dialog for device code authentication
            dialog = DeviceCodeDialog(parent=None)
            dialog.show()
            dialog.on_auth_started()
            
            # We'll use a placeholder client ID that will be replaced at runtime
            # This allows you to fill in your own client ID when you get permission
            client_id = self.config.get("microsoft_auth", {}).get("client_id", "")
            
            if not client_id:
                from PyQt6.QtWidgets import QInputDialog
                client_id, ok = QInputDialog.getText(
                    None, 
                    "Enter Client ID", 
                    "Please enter your Microsoft Azure Application Client ID:",
                    QLineEdit.EchoMode.Normal
                )
                if not ok or not client_id:
                    dialog.reject()
                    return False
                
                # Save the client ID for future use
                ms_auth_config = self.config.get("microsoft_auth", {})
                ms_auth_config["client_id"] = client_id
                self.config.set("microsoft_auth", ms_auth_config)
                self.config.save()
            
            redirect_uri = self.config.get("microsoft_auth", {}).get(
                "redirect_uri", 
                "https://login.microsoftonline.com/common/oauth2/nativeclient"
            )
            
            # Use the secure login method with PKCE
            login_data = minecraft_launcher_lib.microsoft_account.get_secure_login_data(
                client_id, redirect_uri
            )
            
            # Extract the login URL, code verifier, and state
            login_url = login_data["url"]
            code_verifier = login_data["code_verifier"]
            state = login_data["state"]
            
            # Show the dialog with instructions
            dialog.login_url = login_url
            dialog.browser_button.setVisible(True)
            dialog.instruction_label.setText("Sign in to Microsoft using your web browser:")
            dialog.message_label.setText(f"Click the button below to open the login page in your browser.")
            dialog.status_label.setText("Waiting for authentication...")
            
            # Ask the user to enter the redirect URL after authentication
            from PyQt6.QtWidgets import QInputDialog
            
            # Loop until we get a valid auth code or the user cancels
            while True:
                # Process Qt events to keep the UI responsive
                QApplication.processEvents()
                
                # Check if dialog was closed
                if not dialog.isVisible():
                    return False
                    
                # Ask the user for the full redirect URL
                redirect_url, ok = QInputDialog.getText(
                    dialog,
                    "Enter Redirect URL",
                    "After signing in, you will be redirected to a page.\n"
                    "Please copy the FULL URL from your browser's address bar and paste it here:",
                    QLineEdit.EchoMode.Normal,
                    ""
                )
                
                if not ok or not redirect_url:
                    # User canceled
                    dialog.reject()
                    return False
                    
                # Try to parse the auth code and verify the state
                try:
                    auth_result = minecraft_launcher_lib.microsoft_account.parse_auth_code_url(
                        redirect_url, state
                    )
                    
                    if auth_result:
                        # We have a valid auth code
                        auth_code = auth_result["code"]
                        dialog.update_status("Authentication code received! Completing login...")
                        break
                    else:
                        dialog.update_status("Invalid URL or state mismatch. Please try again.")
                except Exception as e:
                    dialog.update_status(f"Error parsing URL: {str(e)}. Please try again.")
            
            # Complete the login process
            try:
                # Complete the login with the code verifier (PKCE)
                minecraft_token = minecraft_launcher_lib.microsoft_account.complete_login(
                    client_id, redirect_uri, auth_code, code_verifier
                )
                
                # Save the authentication data
                self.auth_data = minecraft_token
                self._save_auth_data()
                
                # Update the dialog
                dialog.on_auth_success(minecraft_token)
                
                # Emit success signal
                self.auth_success.emit(minecraft_token)
                
                # Close dialog after short delay to show success
                QTimer.singleShot(2000, dialog.accept)
                return True
                
            except Exception as e:
                dialog.on_auth_error(str(e))
                return False
                
        except Exception as e:
            # Log and emit error
            import traceback
            logging.error(f"Authentication error: {str(e)}")
            logging.error(traceback.format_exc())
            self.auth_error.emit(f"Failed to authenticate: {str(e)}")
            
            # Show error message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "Authentication Error",
                f"Failed to authenticate with Microsoft: {str(e)}"
            )
            return False
    
    def _exchange_token_for_minecraft(self, ms_token):
        """Exchange Microsoft token for Minecraft token."""
        # This is a simplified version - you'd need to implement the full Xbox Live -> Minecraft flow
        # This part would use the Microsoft token to authenticate with Xbox Live,
        # then use the Xbox token to authenticate with Minecraft
        
        try:
            # Step 1: Authenticate with Xbox Live using the Microsoft token
            xbox_auth = minecraft_launcher_lib.xbox_live.authenticate_with_xbox_live(ms_token)
            
            # Step 2: Authenticate with XSTS
            xsts_token = minecraft_launcher_lib.xbox_live.authenticate_with_xsts(xbox_auth)
            
            # Step 3: Authenticate with Minecraft
            minecraft_auth = minecraft_launcher_lib.microsoft_account.authenticate_with_minecraft(xsts_token)
            
            return minecraft_auth
        except Exception as e:
            logging.error(f"Error exchanging tokens: {str(e)}")
            raise
    
    def refresh_login(self) -> bool:
        """Refresh the login tokens if they exist.
        
        Returns:
            bool: True if refresh was successful, False otherwise
        """
        if not self.auth_data or "refresh_token" not in self.auth_data:
            return False
        
        try:
            # Try to refresh the token
            refresh_token = self.auth_data.get("refresh_token")
            if not refresh_token:
                return False
            
            # Use minecraft-launcher-lib to refresh the token
            new_auth_data = minecraft_launcher_lib.microsoft_account.refresh_token(refresh_token)
            
            if not new_auth_data or "error" in new_auth_data:
                logging.error(f"Failed to refresh token: {new_auth_data.get('error', 'Unknown error')}")
                return False
            
            # Update and save the new auth data
            self.auth_data = new_auth_data
            self._save_auth_cache(new_auth_data)
            
            logging.info("Successfully refreshed authentication token")
            return True
            
        except Exception as e:
            logging.error(f"Error refreshing login: {e}")
            return False
    
    def logout(self):
        """Log out the current user."""
        self.auth_data = None
        
        # Delete the cache file if it exists
        if os.path.exists(self.auth_cache_file):
            try:
                os.remove(self.auth_cache_file)
                logging.info("Removed authentication cache file")
            except Exception as e:
                logging.error(f"Failed to remove authentication cache file: {e}")
    
    def set_offline_mode(self, username="Player"):
        """Set authentication to offline mode with a custom username.
        
        Args:
            username (str): Username to use in offline mode
        """
        # Create offline auth data with minimal required fields
        self.auth_data = {
            "name": username,
            "id": "offline-" + hashlib.md5(username.encode()).hexdigest()[:16],
            "access_token": "offline",
            "refresh_token": None,
            "offline_mode": True  # Flag to indicate offline mode
        }
        
        # Emit success signal
        self.auth_success.emit(self.auth_data)
        logging.info(f"Entered offline mode as {username}")
        return True

    def is_offline_mode(self):
        """Check if running in offline mode.
        
        Returns:
            bool: True if in offline mode
        """
        if not hasattr(self, "auth_data") or not self.auth_data:
            return False
        return self.auth_data.get("offline_mode", False)


class DeviceCodeAuthDialog(QDialog):
    """Dialog for device code authentication flow."""
    
    def __init__(self, parent=None):
        """Initialize the device code dialog."""
        super().__init__(parent)
        self.setWindowTitle("Microsoft Authentication")
        self.resize(500, 300)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Instructions
        self.instruction_label = QLabel("To sign in to Minecraft:")
        self.instruction_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.instruction_label)
        
        # Status message
        self.message_label = QLabel("Starting authentication process...")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Code display
        self.code_label = QLabel("")
        self.code_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        self.code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_label.setVisible(False)
        layout.addWidget(self.code_label)
        
        # Open browser button
        self.browser_button = QPushButton("Open login page in browser")
        self.browser_button.clicked.connect(self._open_browser)
        self.browser_button.setVisible(False)
        layout.addWidget(self.browser_button)
        
        # Status indicator
        self.status_label = QLabel("Please wait...")
        layout.addWidget(self.status_label)
        
        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Variables for login info
        self.login_url = ""
        self.auth_code = ""
    
    def _open_browser(self):
        """Open the login URL in a browser."""
        if self.login_url:
            webbrowser.open(self.login_url)
    
    def on_auth_started(self):
        """Handle authentication started event."""
        self.message_label.setText("Starting authentication process...")
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
    
    def on_auth_progress(self, message):
        """Handle authentication progress event.
        
        Args:
            message (str): Progress message
        """
        self.message_label.setText(message)
        
        # Check if the message contains a code
        if "enter code:" in message.lower():
            # Extract the code and URL
            parts = message.split()
            for i, part in enumerate(parts):
                if "http" in part:
                    self.login_url = part
                if "code:" in part and i+1 < len(parts):
                    self.auth_code = parts[i+1]
            
            # Update UI to show code
            if self.auth_code:
                self.code_label.setText(self.auth_code)
                self.code_label.setVisible(True)
                self.browser_button.setVisible(True)
                self.instruction_label.setText("Sign in to Microsoft and enter this code:")
                self.status_label.setText("Waiting for authentication to complete...")
    
    def on_auth_success(self, auth_data):
        """Handle authentication success event.
        
        Args:
            auth_data (dict): Authentication data
        """
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        self.status_label.setText("Authentication successful!")
        self.message_label.setText(f"Successfully logged in as {auth_data.get('name', 'Unknown')}")
        
        # Add OK button and remove Cancel button
        self.button_box.clear()
        self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        
        # Disable browser button
        self.browser_button.setEnabled(False)
    
    def on_auth_error(self, error):
        """Handle authentication error event.
        
        Args:
            error (str): Error message
        """
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.status_label.setText("Authentication failed!")
        self.message_label.setText(f"Error: {error}")
        
        # Show error message
        QMessageBox.critical(
            self,
            "Authentication Error",
            f"Failed to authenticate with Microsoft:\n\n{error}",
            QMessageBox.StandardButton.Ok
        )