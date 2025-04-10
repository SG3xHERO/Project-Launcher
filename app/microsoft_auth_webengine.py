import requests
import json
import os
import uuid
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QApplication, QMessageBox
from app.utils.minecraft_utils import get_player_head

class MicrosoftAuthManager:
    def __init__(self, config=None):
        self.config = config
        
        # Using Minecraft Launcher client ID (already approved)
        self.client_id = "00000000402b5328"
        self.redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        self.scope = "service::user.auth.xboxlive.com::MBI_SSL"
        
        # Load cached tokens if available
        self.token_cache_file = os.path.join(os.path.expanduser("~"), ".minecraft_launcher", "ms_token_cache.json") if config is None else os.path.join(getattr(config, 'app_data_dir', '.'), "ms_token_cache.json")
        self.tokens = self._load_token_cache()
        
    def _load_token_cache(self):
        if os.path.exists(self.token_cache_file):
            try:
                with open(self.token_cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_token_cache(self):
        os.makedirs(os.path.dirname(self.token_cache_file), exist_ok=True)
        with open(self.token_cache_file, 'w') as f:
            json.dump(self.tokens, f)
    
    def authenticate(self):
        """Authenticate with Microsoft"""
        try:
            from app.microsoft_auth_browser import BrowserAuthDialog
            
            # Check if tokens are already available
            if self.tokens and "access_token" in self.tokens:
                logging.info("Using cached tokens for authentication.")
                return True
            
            # Perform authentication via BrowserAuthDialog
            dialog = BrowserAuthDialog(self.client_id, self.redirect_uri)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.auth_code:
                # Simulate token generation for development
                self.tokens = {
                    "access_token": "mock_token_" + str(uuid.uuid4()),
                    "refresh_token": "mock_refresh_" + str(uuid.uuid4()),
                    "username": "Debug1"
                }
                self._save_token_cache()
                return True
            return False
        except Exception as e:
            logging.error(f"Error during authentication: {e}")
            return False

    def get_cached_username(self):
        """Retrieve the cached username if available."""
        return self.tokens.get("username") if self.tokens else None
    
    def get_minecraft_profile(self):
        """Fetch the Minecraft profile with username and UUID."""
        try:
            profile = self._get_minecraft_profile_data()  # Replace with your actual implementation
            if not profile:
                logging.warning("Minecraft profile is None.")
                return None

            # Extract username and UUID
            username = profile.get('name')
            uuid = profile.get('id')

            # Log the fetched data
            logging.info(f"Fetched username: {username}, UUID: {uuid}")

            # Fetch the player's avatar
            from app.utils.minecraft_utils import get_player_head
            avatar = get_player_head(uuid=uuid)

            return {
                'name': username,
                'id': uuid,
                'avatar': avatar
            }
        except Exception as e:
            logging.error(f"Error fetching Minecraft profile: {e}")
            return None

    def _get_minecraft_profile_data(self):
        """Simplified profile for development"""
        return {
            "id": "mock_uuid",
            "name": "Debug2",
            "skins": []
        }
        
    def check_game_ownership(self):
        """Always return True for development"""
        return True

class SimpleMicrosoftLoginDialog(QDialog):
    """A simplified dialog that just asks for a username without real auth."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microsoft Sign In (Development Mode)")
        self.resize(400, 200)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "This is a development version of Microsoft login.\n"
            "Enter any username to continue.\n\n"
            "Real Microsoft authentication will be implemented later."
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        layout.addWidget(self.username_edit)
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.accept)
        layout.addWidget(login_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        self.setLayout(layout)