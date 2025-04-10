from microsoft_auth_browser import setup_qt_webengine, BrowserAuthDialog
import sys
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    # Must call this setup function BEFORE creating QApplication instance
    setup_qt_webengine()
    
    # Now it's safe to create the QApplication
    app = QApplication(sys.argv)
    
    # Initialize your auth dialog
    client_id = "your_client_id"
    redirect_uri = "your_redirect_uri"
    auth_dialog = BrowserAuthDialog(client_id, redirect_uri)
    
    if auth_dialog.exec():
        print(f"Authentication succeeded! Code: {auth_dialog.auth_code}")
    else:
        print("Authentication cancelled or failed")
    
    sys.exit(app.exec())
