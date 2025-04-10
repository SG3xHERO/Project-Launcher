"""
Microsoft Authentication Manager for the Project Launcher.
"""

import logging
import os
import json
import msal
import webbrowser
import time
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QThread, Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QMessageBox, QLabel, QPushButton, QProgressBar
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile

# Import browser auth if using browser-based authentication
try:
    from .microsoft_auth_browser import BrowserAuthDialog
except ImportError:
    BrowserAuthDialog = None

class DeviceCodeDialog(QDialog):
    """Dialog for Microsoft Device Code authentication."""
    
    def __init__(self, code, verification_uri, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Microsoft Authentication")
        self.resize(500, 300)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Instructions
        instruction_label = QLabel("To sign in to Minecraft:")
        instruction_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(instruction_label)
        
        # Message from Microsoft
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Code display
        code_label = QLabel(code)
        code_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Fixed alignment value
        layout.addWidget(code_label)
        
        # Open browser button
        browser_button = QPushButton("Open login page in browser")
        browser_button.clicked.connect(lambda: webbrowser.open(verification_uri))
        layout.addWidget(browser_button)
        
        # Status indicator
        self.status_label = QLabel("Waiting for you to complete authentication...")
        layout.addWidget(self.status_label)
        
        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Auto-open the browser
        QTimer.singleShot(500, lambda: webbrowser.open(verification_uri))

class MicrosoftAuthManager:
    """Manager for Microsoft OAuth authentication flow."""

    # Microsoft OAuth application client ID
    CLIENT_ID = "025c6008-3dca-4e87-a11c-aa9701539663"  # Your client ID
    
    # Microsoft OAuth endpoints - using standard endpoints
    AUTHORITY = "https://login.microsoftonline.com/consumers"
    REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"
    
    # Xbox and Minecraft endpoints
    XBOX_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
    MINECRAFT_XSTS_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
    MINECRAFT_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
    MINECRAFT_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"
    MINECRAFT_ENTITLEMENT_URL = "https://api.minecraftservices.com/entitlements/mcstore"
    
    # Updated scopes required for accessing Xbox Live and Minecraft services
    SCOPES = ["XboxLive.signin", "XboxLive.offline_access"]
    
    def __init__(self, config=None):
        """Initialize the auth manager."""
        self.config = config
        self.token_cache = msal.SerializableTokenCache()
        
        # Try to load existing token cache
        if self.config:
            try:
                # Get the token cache without using fallback
                cache_data = self.config.get('auth', 'ms_token_cache')
                if cache_data:
                    self.token_cache.deserialize(cache_data)
                    logging.info("Loaded Microsoft token cache from configuration")
            except Exception as e:
                # This will handle both KeyError (if ms_token_cache doesn't exist)
                # and any deserialization errors
                logging.error(f"Failed to load token cache: {e}")
    
    def _get_public_client(self):
        """Get the MSAL public client application."""
        return msal.PublicClientApplication(
            client_id=self.CLIENT_ID,
            authority=self.AUTHORITY,
            token_cache=self.token_cache
        )
    
    def authenticate(self):
        """Authenticate the user with Microsoft."""
        try:
            # Get the MSAL public client
            client = self._get_public_client()
            
            # Check if we already have a cached account
            accounts = client.get_accounts()
            if accounts:
                logging.info("Found existing Microsoft account in cache")
                result = client.acquire_token_silent(
                    scopes=self.SCOPES,
                    account=accounts[0]
                )
                if result and "access_token" in result:
                    logging.info("Successfully acquired token from cache")
                    self._save_token_cache()
                    return True
            
            # Try device code flow first (more reliable)
            return self._authenticate_device_code(client)
                
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            logging.exception("Authentication exception details:")
            return False
    
    def _authenticate_device_code(self, client):
        """Use device code flow for authentication."""
        try:
            # This is a direct approach to device code flow without a dialog
            # It's simpler and more reliable
            
            # Start device code flow
            flow = client.initiate_device_flow(scopes=self.SCOPES)
            
            if "user_code" not in flow:
                error_msg = flow.get('error_description', flow.get('error', 'Unknown error'))
                logging.error(f"Failed to start device code flow: {error_msg}")
                
                # Show error to user
                QMessageBox.critical(
                    None, 
                    "Authentication Error",
                    f"Failed to start authentication:\n\n{error_msg}"
                )
                return False
            
            # Show the code to the user
            user_code = flow["user_code"]
            verification_uri = flow["verification_uri"]
            message = flow["message"]
            
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Microsoft Authentication")
            msg_box.setText(f"To sign in to your Microsoft account:\n\n1. Visit: {verification_uri}\n\n2. Enter code: {user_code}")
            msg_box.setInformativeText("Your browser should open automatically. This window will update once you complete the sign-in process.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            # Open the browser automatically
            webbrowser.open(verification_uri)
            
            # Show the dialog
            choice = msg_box.exec()
            
            if choice == QMessageBox.StandardButton.Cancel:
                logging.warning("User cancelled device code authentication")
                return False
            
            # Now we need to poll for the result
            progress_dialog = QDialog(None)
            progress_dialog.setWindowTitle("Waiting for Authentication")
            progress_dialog.setFixedSize(400, 100)
            
            dialog_layout = QVBoxLayout(progress_dialog)
            status_label = QLabel("Please complete the authentication in your browser...")
            dialog_layout.addWidget(status_label)
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 0)  # Indeterminate
            dialog_layout.addWidget(progress_bar)
            
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(progress_dialog.reject)
            dialog_layout.addWidget(cancel_button)
            
            # Create a timer to poll for token acquisition
            interval = flow.get("interval", 5)
            timer = QTimer(progress_dialog)
            
            # Flag to track cancellation
            cancelled = [False]
            
            def check_token():
                if cancelled[0]:
                    return
                
                result = client.acquire_token_by_device_flow(flow)
                
                if "access_token" in result:
                    # Success! Save token and close dialog
                    self._save_token_cache()
                    status_label.setText("Authentication successful!")
                    progress_dialog.accept()
                elif "error" in result:
                    if result["error"] != "authorization_pending":
                        # Real error (not just waiting)
                        error_msg = result.get('error_description', result['error'])
                        logging.error(f"Device code error: {error_msg}")
                        status_label.setText(f"Error: {error_msg}")
                        progress_bar.setVisible(False)
                        cancel_button.setText("Close")
                        timer.stop()
            
            # Connect timer to check function
            timer.timeout.connect(check_token)
            timer.start(interval * 1000)  # Convert to milliseconds
            
            # Handle dialog closure
            def on_dialog_closed():
                cancelled[0] = True
                timer.stop()
            
            progress_dialog.rejected.connect(on_dialog_closed)
            
            # Show the progress dialog and wait
            result = progress_dialog.exec()
            
            # Stop the timer if it's still running
            if timer.isActive():
                timer.stop()
            
            if result == QDialog.DialogCode.Accepted:
                logging.info("Device code authentication successful")
                return True
            else:
                logging.warning("Device code authentication cancelled or failed")
                return False
            
        except Exception as e:
            logging.error(f"Device code authentication error: {e}")
            logging.exception("Device code authentication exception details:")
            
            # Show error to user
            QMessageBox.critical(
                None, 
                "Authentication Error",
                f"An error occurred during authentication:\n\n{str(e)}"
            )
            return False
    
    def _save_token_cache(self):
        """Save the token cache to configuration."""
        if self.config and self.token_cache.has_state_changed:
            try:
                # Check how the config's set method works
                # Option 1: If your Config.set() takes key and value only
                self.config.set('ms_token_cache', self.token_cache.serialize())
            except TypeError:
                try:
                    # Option 2: If your Config has a different approach for auth data
                    if hasattr(self.config, 'set_auth'):
                        self.config.set_auth('ms_token_cache', self.token_cache.serialize())
                    else:
                        # Option 3: Directly modify the config's internal structure if possible
                        if not hasattr(self.config, 'config'):
                            self.config.config = {}
                        if 'auth' not in self.config.config:
                            self.config.config['auth'] = {}
                        self.config.config['auth']['ms_token_cache'] = self.token_cache.serialize()
                        self.config.save()
                except Exception as e:
                    logging.error(f"Failed to save token cache: {e}")
            logging.info("Saved Microsoft token cache to configuration")
    
    def get_minecraft_profile(self):
        """Get the Minecraft profile data for the authenticated user."""
        try:
            # Get access token
            client = self._get_public_client()
            accounts = client.get_accounts()
            
            if not accounts:
                logging.error("No Microsoft account found in cache")
                return None
                
            result = client.acquire_token_silent(
                scopes=self.SCOPES,
                account=accounts[0]
            )
            
            if not result or "access_token" not in result:
                logging.error("Failed to acquire Microsoft access token")
                return None
                
            # Authenticate with Xbox Live
            import requests
            
            # Xbox Live authentication
            xbl_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            xbl_data = {
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={result['access_token']}"
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT"
            }
            
            # Detailed logging for debugging
            logging.info("Authenticating with Xbox Live")
            
            xbl_response = requests.post(
                self.XBOX_AUTH_URL,
                json=xbl_data,
                headers=xbl_headers
            )
            
            if xbl_response.status_code != 200:
                logging.error(f"Xbox Live authentication failed: {xbl_response.status_code}")
                logging.error(f"Response: {xbl_response.text}")
                return None
                
            xbl_token = xbl_response.json()["Token"]
            user_hash = xbl_response.json()["DisplayClaims"]["xui"][0]["uhs"]
            
            # XSTS authentication
            logging.info("Authenticating with XSTS")
            
            xsts_data = {
                "Properties": {
                    "SandboxId": "RETAIL",
                    "UserTokens": [xbl_token]
                },
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT"
            }
            
            xsts_response = requests.post(
                self.MINECRAFT_XSTS_URL,
                json=xsts_data,
                headers=xbl_headers
            )
            
            if xsts_response.status_code != 200:
                logging.error(f"XSTS authentication failed: {xsts_response.status_code}")
                logging.error(f"Response: {xsts_response.text}")
                return None
                
            xsts_token = xsts_response.json()["Token"]
            
            # Minecraft authentication
            logging.info("Authenticating with Minecraft services")
            
            mc_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            mc_data = {
                "identityToken": f"XBL3.0 x={user_hash};{xsts_token}"
            }
            
            mc_response = requests.post(
                self.MINECRAFT_LOGIN_URL,
                json=mc_data,
                headers=mc_headers
            )
            
            if mc_response.status_code != 200:
                logging.error(f"Minecraft authentication failed: {mc_response.status_code}")
                logging.error(f"Response: {mc_response.text}")
                return None
                
            mc_access_token = mc_response.json()["access_token"]
            
            # Check if the user actually owns Minecraft
            logging.info("Checking Minecraft entitlements")
            entitlement_headers = {
                "Authorization": f"Bearer {mc_access_token}"
            }
            
            entitlement_response = requests.get(
                self.MINECRAFT_ENTITLEMENT_URL,
                headers=entitlement_headers
            )
            
            if entitlement_response.status_code != 200:
                logging.error(f"Failed to get Minecraft entitlements: {entitlement_response.status_code}")
                return None
                
            entitlements = entitlement_response.json()
            
            # Check if the user owns Minecraft
            if not entitlements.get("items", []):
                logging.warning("User does not own Minecraft")
                # You may want to handle this case specially
            
            # Get Minecraft profile
            logging.info("Getting Minecraft profile")
            profile_headers = {
                "Authorization": f"Bearer {mc_access_token}"
            }
            
            profile_response = requests.get(
                self.MINECRAFT_PROFILE_URL,
                headers=profile_headers
            )
            
            if profile_response.status_code != 200:
                logging.error(f"Failed to get Minecraft profile: {profile_response.status_code}")
                logging.error(f"Response: {profile_response.text}")
                return None
            
            # Return profile with access token for game launches
            profile_data = profile_response.json()
            profile_data["access_token"] = mc_access_token
            return profile_data
            
        except Exception as e:
            logging.error(f"Error getting Minecraft profile: {e}")
            logging.exception("Profile error details:")
            return None