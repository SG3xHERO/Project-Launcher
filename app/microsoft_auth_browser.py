import msal
import webbrowser
import json
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt

class BrowserAuthDialog(QDialog):
    def __init__(self, client_id, redirect_uri):
        super().__init__()
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.auth_code = None
        
        self.setWindowTitle("Microsoft Sign In")
        self.resize(400, 150)
        
        layout = QVBoxLayout()
        
        # Instructions
        layout.addWidget(QLabel("1. Click 'Open Browser' to sign in with Microsoft"))
        layout.addWidget(QLabel("2. After signing in, you will be redirected to a page"))
        layout.addWidget(QLabel("3. Copy the authorization code from the URL after 'code='"))
        
        # Button to open browser
        self.browser_button = QPushButton("Open Browser for Sign In")
        self.browser_button.clicked.connect(self.open_browser)
        layout.addWidget(self.browser_button)
        
        # Input for auth code
        layout.addWidget(QLabel("Authorization Code:"))
        self.code_input = QLineEdit()
        layout.addWidget(self.code_input)
        
        # Buttons
        button_layout = QVBoxLayout()
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.accept_code)
        button_layout.addWidget(self.submit_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def open_browser(self):
        # Build the auth URL
        auth_url = (
            "https://login.live.com/oauth20_authorize.srf"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope=service::user.auth.xboxlive.com::MBI_SSL"
        )
        
        # Open the default web browser
        webbrowser.open(auth_url)
    
    def accept_code(self):
        code = self.code_input.text().strip()
        if code:
            self.auth_code = code
            self.accept()
        else:
            QMessageBox.warning(self, "Missing Code", "Please enter the authorization code.")