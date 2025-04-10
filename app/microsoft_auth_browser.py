import msal
import webbrowser
import json
import os
import logging
from urllib.parse import urlparse, parse_qs
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QDialogButtonBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile

def setup_qt_webengine():
    """
    Set up the required Qt WebEngine settings.
    Must be called before creating a QApplication instance.
    """
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

class BrowserAuthDialog(QDialog):
    """Dialog that displays the Microsoft login page and captures the authorization code."""
    
    def __init__(self, client_id, redirect_uri, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.auth_code = None
        
        self.setWindowTitle("Microsoft Authentication")
        self.resize(800, 700)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Please sign in with your Microsoft account...")
        layout.addWidget(self.status_label)
        
        # Create a web view
        self.web_view = QWebEngineView()
        
        # Create a custom profile to avoid cache issues
        profile = QWebEngineProfile("Microsoft_Auth_Profile", self.web_view)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        
        # Load Microsoft OAuth URL
        login_url = self._build_auth_url()
        logging.debug(f"Loading Microsoft OAuth URL: {login_url}")
        
        self.web_view.setUrl(QUrl(login_url))
        self.web_view.urlChanged.connect(self._url_changed)
        layout.addWidget(self.web_view)
        
        # Add cancel button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _build_auth_url(self):
        """Build the Microsoft OAuth URL."""
        url = "https://login.live.com/oauth20_authorize.srf"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "XboxLive.signin offline_access",
            "prompt": "select_account"
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
                self.accept()  # Close dialog with "accept" result
            elif "error" in query_params:
                error = query_params["error"][0]
                error_description = query_params.get("error_description", ["Unknown error"])[0]
                logging.error(f"Authentication error: {error} - {error_description}")
                self.status_label.setText(f"Authentication error: {error_description}")
                # Keep dialog open to show error
            else:
                logging.warning(f"Redirect URI reached without code or error: {url_str}")