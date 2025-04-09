import msal
import requests
import webbrowser
import json
import os
import uuid
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QApplication, QMessageBox
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QEventLoop
from PyQt6.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor

class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.redirect_url = None
        
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        if url.startswith("https://login.live.com/oauth20_desktop.srf"):
            self.redirect_url = url

class MicrosoftAuthManager:
    def __init__(self, config):
        self.config = config
        
        # Using Minecraft Launcher client ID (already approved)
        self.client_id = "00000000402b5328"
        self.redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        self.scope = "service::user.auth.xboxlive.com::MBI_SSL"
        
        # Load cached tokens if available
        self.token_cache_file = os.path.join(config.app_data_dir, "ms_token_cache.json")
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
        with open(self.token_cache_file, 'w') as f:
            json.dump(self.tokens, f)
    
    def authenticate(self):
        """Start the Microsoft authentication flow using external browser"""
        auth_dialog = BrowserAuthDialog(self.client_id, self.redirect_uri)
        
        if auth_dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the authorization code
            code = auth_dialog.auth_code
            
            # Exchange code for token
            payload = {
                'client_id': self.client_id,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            try:
                response = requests.post('https://login.live.com/oauth20_token.srf', data=payload)
                
                if response.status_code != 200:
                    QMessageBox.critical(None, "Authentication Error", 
                                      f"Failed to obtain access token. Status code: {response.status_code}")
                    return False
                    
                data = response.json()
                ms_token = data['access_token']
                
                # Get Xbox Live token
                xbox_token_data = self._get_xbox_live_token(ms_token)
                if not xbox_token_data:
                    return False
                    
                # Get XSTS token
                xsts_token_data = self._get_xsts_token(xbox_token_data)
                if not xsts_token_data:
                    return False
                    
                # Get Minecraft token
                minecraft_data = self._get_minecraft_token(xsts_token_data)
                if not minecraft_data:
                    return False
                
                # Store tokens and profile
                self.tokens = {
                    "microsoft": ms_token,
                    "xbox": xbox_token_data,
                    "xsts": xsts_token_data,
                    "minecraft": minecraft_data
                }
                self._save_token_cache()
                return True
                
            except Exception as e:
                QMessageBox.critical(None, "Authentication Error", f"Failed during authentication: {str(e)}")
                return False
                
        return False

    def _get_xbox_live_token(self, ms_token):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        payload = {
            'Properties': {
                'AuthMethod': 'RPS',
                'SiteName': 'user.auth.xboxlive.com',
                'RpsTicket': f'd={ms_token}'
            },
            'RelyingParty': 'http://auth.xboxlive.com',
            'TokenType': 'JWT'
        }
        response = requests.post('https://user.auth.xboxlive.com/user/authenticate', 
                               json=payload, headers=headers)
                               
        if response.status_code != 200:
            return None
        
        data = response.json()
        return {
            'token': data['Token'],
            'user_hash': data['DisplayClaims']['xui'][0]['uhs']
        }
    
    def _get_xsts_token(self, xbox_data):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        payload = {
            'Properties': {
                'SandboxId': 'RETAIL',
                'UserTokens': [xbox_data['token']]
            },
            'RelyingParty': 'rp://api.minecraftservices.com/',
            'TokenType': 'JWT'
        }
        response = requests.post('https://xsts.auth.xboxlive.com/xsts/authorize', 
                               json=payload, headers=headers)
                               
        if response.status_code != 200:
            return None
            
        data = response.json()
        return {
            'token': data['Token'],
            'user_hash': data['DisplayClaims']['xui'][0]['uhs']
        }
    
    def _get_minecraft_token(self, xsts_data):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        payload = {
            'identityToken': f"XBL3.0 x={xsts_data['user_hash']};{xsts_data['token']}"
        }
        response = requests.post('https://api.minecraftservices.com/authentication/login_with_xbox', 
                              json=payload, headers=headers)
                              
        if response.status_code != 200:
            return None
            
        return response.json()
    
    def get_minecraft_profile(self):
        """Get the current user's Minecraft profile"""
        if not self.tokens.get("minecraft"):
            return None
        
        mc_token = self.tokens["minecraft"]["access_token"]
        headers = {
            'Authorization': f'Bearer {mc_token}'
        }
        
        response = requests.get('https://api.minecraftservices.com/minecraft/profile', headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
        
    def check_game_ownership(self):
        """Check if the user owns Minecraft"""
        if not self.tokens.get("minecraft"):
            return False
            
        mc_token = self.tokens["minecraft"]["access_token"]
        headers = {
            'Authorization': f'Bearer {mc_token}'
        }
        
        response = requests.get('https://api.minecraftservices.com/entitlements/mcstore', headers=headers)
        if response.status_code == 200:
            return len(response.json().get('items', [])) > 0
        return False


class MicrosoftAuthDialog(QDialog):
    def __init__(self, client_id, redirect_uri, scope):
        super().__init__()
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.access_token = None
        
        self.setWindowTitle("Microsoft Sign In")
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Create web view for authentication
        self.interceptor = RequestInterceptor()
        self.browser = QWebEngineView()
        page = QWebEnginePage(self.browser)
        page.profile().setUrlRequestInterceptor(self.interceptor)
        self.browser.setPage(page)
        
        # Generate state parameter for security
        state = str(uuid.uuid4())
        
        # Build the auth URL
        auth_url = (
            "https://login.live.com/oauth20_authorize.srf"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={self.scope}"
            f"&state={state}"
        )
        
        # Load the URL in the web view
        self.browser.load(QUrl(auth_url))
        layout.addWidget(self.browser)
        
        self.setLayout(layout)
        
        # Setup timer to check for redirect URL
        self.timer = self.startTimer(100)
        
    def timerEvent(self, event):
        if self.interceptor.redirect_url:
            self.killTimer(self.timer)
            url = self.interceptor.redirect_url
            
            if "code=" in url:
                code = url.split("code=")[1].split("&")[0]
                self._exchange_code_for_token(code)
            else:
                self.reject()
    
    def _exchange_code_for_token(self, code):
        payload = {
            'client_id': self.client_id,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post('https://login.live.com/oauth20_token.srf', data=payload)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data['access_token']
            self.accept()
        else:
            self.reject()