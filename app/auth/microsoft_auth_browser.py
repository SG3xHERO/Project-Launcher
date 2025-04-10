"""
Browser-based Microsoft authentication dialog for Project Launcher.
"""

import logging
from urllib.parse import urlparse, parse_qs
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox, QDialogButtonBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

class CustomWebEnginePage(QWebEnginePage):
    """Custom web engine page to handle certificate errors."""
    
    def certificateError(self, error):
        """Handle certificate errors during page loading."""
        logging.warning(f"Certificate error: {error.errorDescription()}")
        return False  # Don't ignore certificate errors for security

class BrowserAuthDialog(QDialog):
    """Dialog that displays the Microsoft login page and captures the authorization code."""
    
    # Signal emitted during the authentication process
    auth_status = pyqtSignal(str)
    
    def __init__(self, client_id, redirect_uri, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.auth_code = None
        
        self.setWindowTitle("Microsoft Authentication")
        self.resize(800, 700)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Status label with improved styling
        self.status_label = QLabel("Please sign in with your Microsoft account to access Minecraft.")
        self.status_label.setStyleSheet("font-size: 14px; color: #0078D7; margin-bottom: 10px;")
        layout.addWidget(self.status_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Create a web view with custom page
        self.web_view = QWebEngineView()
        custom_page = CustomWebEnginePage(self.web_view)
        self.web_view.setPage(custom_page)
        
        # Create a custom profile to avoid cache issues
        profile = QWebEngineProfile("Microsoft_Auth_Profile", self.web_view)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        
        # Connect signals
        self.web_view.loadProgress.connect(self.progress_bar.setValue)
        self.web_view.loadStarted.connect(self._on_load_started)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.urlChanged.connect(self._url_changed)
        
        # Load Microsoft OAuth URL
        login_url = self._build_auth_url()
        logging.debug(f"Loading Microsoft OAuth URL: {login_url}")
        
        self.web_view.setUrl(QUrl(login_url))
        layout.addWidget(self.web_view)
        
        # Button box with cancel and help buttons
        buttons = QDialogButtonBox()
        self.cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self.help_button = buttons.addButton("Help", QDialogButtonBox.ButtonRole.HelpRole)
        self.try_device_button = buttons.addButton("Try Device Code Instead", QDialogButtonBox.ButtonRole.ActionRole)
        
        self.cancel_button.clicked.connect(self.reject)
        self.help_button.clicked.connect(self._show_help)
        self.try_device_button.clicked.connect(self._try_device_code)
        
        layout.addWidget(buttons)
        
        # Center the dialog on the screen
        self.setMinimumWidth(640)
        self.setMinimumHeight(580)
        
    def get_auth_code(self):
        """Return the authorization code after successful authentication."""
        return self.auth_code
        
    def _build_auth_url(self):
        """Build the Microsoft OAuth URL with improved parameters."""
        # Use a different approach - use login.live.com directly which works better for public clients
        url = "https://login.live.com/oauth20_authorize.srf"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "XboxLive.signin offline_access",
            "prompt": "select_account",
        }
        
        # Build query string
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{url}?{query}"
    
    def _url_changed(self, url):
        """Handle URL changes in the web view."""
        url_str = url.toString()
        logging.debug(f"URL changed: {url_str}")
        
        # Check if redirected to our redirect URI
        if url_str.startswith(self.redirect_uri):
            # Parse the URL to extract the authorization code
            parsed_url = urlparse(url_str)
            query_params = parse_qs(parsed_url.query)
            
            if "code" in query_params:
                self.auth_code = query_params["code"][0]
                logging.info("Successfully obtained authentication code")
                self.status_label.setText("Authentication successful! Completing login...")
                self.auth_status.emit("Success")
                self.accept()  # Close dialog with "accept" result
            elif "error" in query_params:
                error = query_params["error"][0]
                error_description = query_params.get("error_description", ["Unknown error"])[0]
                logging.error(f"Authentication error: {error} - {error_description}")
                
                # Improved error display
                self.status_label.setText(f"Authentication error: {error}")
                self.status_label.setStyleSheet("font-size: 14px; color: #D83B01; margin-bottom: 10px;")
                
                # Show detailed error message
                QMessageBox.critical(
                    self,
                    "Authentication Error",
                    f"Failed to authenticate with Microsoft:\n\n{error_description}\n\nPlease try again or use the device code method.",
                    QMessageBox.StandardButton.Ok
                )
                
                # Keep dialog open to allow retry
            else:
                logging.warning(f"Redirect URI reached without code or error: {url_str}")
    
    def _on_load_started(self):
        """Handle web view load started event."""
        self.status_label.setText("Loading Microsoft login page...")
        self.progress_bar.setVisible(True)
    
    def _on_load_finished(self, success):
        """Handle web view load finished event."""
        if success:
            self.status_label.setText("Please sign in with your Microsoft account.")
        else:
            self.status_label.setText("Failed to load the login page. Please check your internet connection.")
            self.status_label.setStyleSheet("font-size: 14px; color: #D83B01; margin-bottom: 10px;")
        
        # Hide progress bar after loading
        self.progress_bar.setVisible(False)
    
    def _show_help(self):
        """Show a help dialog with troubleshooting information."""
        help_text = (
            "<h3>Microsoft Authentication Help</h3>"
            "<p>If you're having trouble signing in:</p>"
            "<ul>"
            "<li>Make sure you're using a Microsoft account that owns Minecraft</li>"
            "<li>Check your internet connection</li>"
            "<li>Try clearing your browser cookies and cache</li>"
            "<li>Make sure you're using the correct Microsoft account</li>"
            "<li>If you use 2FA, have your authentication device ready</li>"
            "<li>Try the 'Device Code' authentication method instead, which is often more reliable</li>"
            "</ul>"
            "<p>For more help, visit <a href='https://help.minecraft.net/'>Minecraft Support</a>.</p>"
        )
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Authentication Help")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(help_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
    
    def _try_device_code(self):
        """Close this dialog and signal to try device code flow instead."""
        self.done(2)  # Use a custom return code (2) to indicate switching to device code