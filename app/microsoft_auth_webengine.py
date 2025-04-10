import requests
import json
import os
import uuid
import logging
import time
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QApplication, QMessageBox
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from app.utils.minecraft_utils import get_player_head
from msal import PublicClientApplication, SerializableTokenCache

class BrowserAuthDialog(QDialog):
    """Dialog that displays the Microsoft login page and captures the authorization code."""
    
    def __init__(self, client_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.auth_code = None
        # Update to use the Live login redirect URI
        self.redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        
        self.setWindowTitle("Microsoft Authentication")
        self.setMinimumSize(800, 650)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Label with instructions
        instructions = QLabel("Please sign in with your Microsoft account. The window will close automatically when authentication is complete.")
        layout.addWidget(instructions)
        
        # Create web view for login
        self.web_view = QWebEngineView()
        
        # Create a clean, private profile for this session
        profile = QWebEngineProfile("MicrosoftAuth", self.web_view)
        
        # Connect to URL changed signal to capture auth code
        self.web_view.urlChanged.connect(self._url_changed)
        
        # Load the Microsoft auth URL
        auth_url = self._build_auth_url()
        logging.info(f"Loading auth URL: {auth_url}")
        self.web_view.load(QUrl(auth_url))
        layout.addWidget(self.web_view)
        
        # Add cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        self.setLayout(layout)
    
    def get_auth_code(self):
        """Return the authorization code after successful authentication."""
        return self.auth_code
    
    def _build_auth_url(self):
        """Build the Microsoft OAuth authorization URL."""
        # Use the Xbox Live auth endpoint directly instead of Microsoft's general OAuth endpoint
        return (
            f"https://login.live.com/oauth20_authorize.srf"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope=XboxLive.signin%20XboxLive.offline_access"
            f"&prompt=select_account"
        )
    
    def _url_changed(self, url):
        """Handle URL changes to detect authentication completion."""
        url_str = url.toString()
        logging.info(f"URL changed to: {url_str}")
        
        # Check if we're at the redirect URI with an auth code
        if url_str.startswith(self.redirect_uri):
            # Extract the authorization code
            fragment = url.fragment()
            logging.info(f"Fragment: {fragment}")
            
            if "code=" in fragment:
                # Parse the fragment
                params = {}
                for param in fragment.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        params[key] = value
                
                if "code" in params:
                    self.auth_code = params["code"]
                    logging.info("Successfully obtained authorization code")
                    self.accept()
                else:
                    logging.warning("No code found in redirect URI fragment")
                    self.reject()
            else:
                logging.warning("Authentication failed or was cancelled by the user")
                self.reject()

class MicrosoftAuthManager:
    def __init__(self, config=None):
        self.config = config
        
        # Use Minecraft's official client ID - properly formatted (this is likely the issue)
        self.client_id = "389b1b32-b5d5-43b2-bddc-84ce938d6737"  # More reliable client ID
        # Use Microsoft Live login endpoint
        self.redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        self.scopes = ["XboxLive.signin", "XboxLive.offline_access"]
        
        # Use a consistent path for the token cache
        self.token_cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ms_token_cache.json") if config is None else os.path.join(getattr(config, 'app_data_dir', '.'), "ms_token_cache.json")
        self.tokens = self._load_token_cache()
        
    def _get_public_client(self):
        """Create and return a public client application for authentication."""
        # Create the MSAL token cache
        cache = SerializableTokenCache()
        
        # If we have existing cache data, deserialize it
        if self.tokens:
            try:
                cache.deserialize(json.dumps(self.tokens))
            except Exception as e:
                logging.warning(f"Failed to deserialize token cache: {e}")
        
        # Use the proper authority for Microsoft consumer accounts
        return PublicClientApplication(
            client_id=self.client_id,
            authority="https://login.live.com/",
            token_cache=cache
        )
    
    def _load_token_cache(self):
        if os.path.exists(self.token_cache_file):
            try:
                with open(self.token_cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_token_to_cache(self, token_data):
        """Save token data to cache file with expiry time."""
        if "expires_in" in token_data:
            # Calculate absolute expiry time
            token_data["expires_at"] = time.time() + token_data["expires_in"]
        
        # Save to the instance and to the file
        self.tokens = token_data
        self._save_token_cache()
    
    def _load_token_from_cache(self):
        """Load token from cache file but verify it's still valid."""
        try:
            if os.path.exists(self.token_cache_file):
                with open(self.token_cache_file, 'r') as f:
                    cached = json.load(f)
                    
                # Check if token is still valid (not expired)
                if 'expires_at' in cached:
                    expiry_time = cached['expires_at']
                    current_time = time.time()
                    
                    # If token expires in less than 5 minutes, consider it expired
                    if expiry_time - current_time < 300:
                        logging.info("Cached token is expired or expiring soon")
                        return None
                        
                return cached
            return None
        except Exception as e:
            logging.error(f"Error loading token from cache: {e}")
            return None
    
    def _save_token_cache(self):
        os.makedirs(os.path.dirname(self.token_cache_file), exist_ok=True)
        with open(self.token_cache_file, 'w') as f:
            json.dump(self.tokens, f)
    
    def authenticate(self):
        """Authenticate the user with Microsoft."""
        try:
            # Use browser authentication since interactive MSAL auth can be problematic
            auth_dialog = BrowserAuthDialog(client_id=self.client_id)
            
            if auth_dialog.exec() == QDialog.DialogCode.Accepted:
                auth_code = auth_dialog.get_auth_code()
                if not auth_code:
                    logging.warning("No authorization code received")
                    return False
                
                # Get the MSAL public client
                client = self._get_public_client()
                
                # Exchange the code for tokens
                result = client.acquire_token_by_authorization_code(
                    code=auth_code,
                    scopes=self.scopes,
                    redirect_uri=self.redirect_uri
                )
                
                # Process the result
                if result and "access_token" in result:
                    self._save_token_to_cache(result)
                    logging.info("Microsoft authentication successful")
                    return True
                else:
                    error = result.get("error") if result else "No result"
                    error_description = result.get("error_description") if result else "Unknown error"
                    logging.warning(f"Token acquisition failed: {error} - {error_description}")
                    return False
            else:
                logging.warning("Authentication was cancelled by user")
                return False
                
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            logging.exception("Authentication exception details:")
            return False

    def get_cached_username(self):
        """Retrieve the cached username if available."""
        return self.tokens.get("username") if self.tokens else None
    
    def get_minecraft_profile(self):
        """Fetch the Minecraft profile with username and UUID."""
        try:
            profile = self._get_minecraft_profile_data()
            if not profile:
                logging.error("Failed to get Minecraft profile data")
                return None

            # Extract profile data with detailed logging
            username = profile.get('name')
            player_uuid = profile.get('id')
            
            if not username:
                logging.error("No username found in profile data")
                return None
                
            if not player_uuid:
                logging.error("No UUID found in profile data")
                return None
                
            logging.info(f"Successfully retrieved Minecraft profile: {username} ({player_uuid})")
            
            # Get avatar if available
            try:
                avatar = get_player_head(uuid=player_uuid)
            except Exception as avatar_error:
                logging.error(f"Failed to get avatar: {avatar_error}")
                avatar = None
            
            return {
                'name': username,
                'id': player_uuid,
                'avatar': avatar
            }
        except Exception as e:
            logging.error(f"Error fetching Minecraft profile: {e}")
            logging.exception("Full exception details:")
            return None

    def _get_minecraft_profile_data(self):
        """Internal method to fetch Minecraft profile data."""
        try:
            if not self.tokens or "access_token" not in self.tokens:
                logging.error("No tokens available. Authentication may have failed.")
                return None
                
            # Get Xbox Live token
            xbox_live_token = self._authenticate_with_xbox(self.tokens["access_token"])
            if not xbox_live_token:
                return None
                
            # Get XSTS token
            xsts_token = self._authenticate_with_xsts(xbox_live_token)
            if not xsts_token:
                return None
                
            # Get Minecraft token
            minecraft_token = self._authenticate_with_minecraft(xsts_token)
            if not minecraft_token:
                return None
                
            # Get Minecraft profile
            return self._get_minecraft_profile(minecraft_token)
            
        except Exception as e:
            logging.error(f"Error in _get_minecraft_profile_data: {e}")
            logging.exception("Exception details:")
            return None
            
    def _authenticate_with_xbox(self, ms_token):
        """Convert Microsoft token to Xbox Live token."""
        url = "https://user.auth.xboxlive.com/user/authenticate"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={ms_token}"
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["Token"]
        else:
            logging.error(f"Xbox Live authentication failed: {response.status_code}")
            return None
            
    def _authenticate_with_xsts(self, xbox_token):
        """Convert Xbox Live token to XSTS token."""
        url = "https://xsts.auth.xboxlive.com/xsts/authorize"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [xbox_token]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return {
                "token": data["Token"],
                "uhs": data["DisplayClaims"]["xui"][0]["uhs"]
            }
        else:
            logging.error(f"XSTS authentication failed: {response.status_code}")
            return None
            
    def _authenticate_with_minecraft(self, xsts_data):
        """Convert XSTS token to Minecraft token."""
        url = "https://api.minecraftservices.com/authentication/login_with_xbox"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "identityToken": f"XBL3.0 x={xsts_data['uhs']};{xsts_data['token']}"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            logging.error(f"Minecraft authentication failed: {response.status_code}")
            return None
            
    def _get_minecraft_profile(self, minecraft_token):
        """Get Minecraft profile using Minecraft token."""
        url = "https://api.minecraftservices.com/minecraft/profile"
        headers = {
            "Authorization": f"Bearer {minecraft_token}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Profile retrieval failed: {response.status_code}")
            return None
        
    def check_game_ownership(self):
        """Check if the user owns Minecraft."""
        # In a real implementation, you would check the game ownership API
        return True