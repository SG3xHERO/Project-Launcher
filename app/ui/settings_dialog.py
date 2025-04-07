#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings dialog for the Minecraft Modpack Launcher.
"""

import os
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTabWidget, QWidget,
    QFormLayout, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QSettings

class ModernLineEdit(QLineEdit):
    """Modern styled line edit with rounded corners."""
    
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2B3142;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                background-color: #323848;
            }
        """)

class ModernButton(QPushButton):
    """Modern styled button with rounded corners and hover effects."""
    
    def __init__(self, text, accent=False, parent=None):
        super().__init__(text, parent)
        self.accent = accent
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Set style based on button type
        if accent:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #E61B72;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F32A81;
                }
                QPushButton:pressed {
                    background-color: #D10A61;
                }
                QPushButton:disabled {
                    background-color: #444B5A;
                    color: #8D93A0;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2B3142;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #363D51;
                }
                QPushButton:pressed {
                    background-color: #222736;
                }
                QPushButton:disabled {
                    background-color: #232734;
                    color: #6D727E;
                }
            """)

class SettingsDialog(QDialog):
    """Settings dialog for the Minecraft Modpack Launcher."""
    
    def __init__(self, config, parent=None):
        """Initialize settings dialog.
        
        Args:
            config: Configuration instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config = config
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1C23;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTabWidget::pane {
                border: none;
                background-color: #1A1C23;
            }
            QTabBar::tab {
                background-color: #2B3142;
                color: white;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 100px;
                padding: 8px 16px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #E61B72;
            }
            QTabBar::tab:hover:!selected {
                background-color: #363D51;
            }
            QLabel {
                color: white;
            }
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                background-color: #2B3142;
            }
            QCheckBox::indicator:checked {
                background-color: #E61B72;
                image: url('app/ui/resources/checkmark.png');
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # General settings tab
        self.general_tab = QWidget()
        general_layout = QVBoxLayout(self.general_tab)
        general_layout.setContentsMargins(20, 20, 20, 20)
        general_layout.setSpacing(15)
        
        # Repository settings
        repository_form = QFormLayout()
        repository_form.setSpacing(10)
        
        self.repo_url_edit = ModernLineEdit(placeholder="https://example.com:5000")
        repository_form.addRow("Repository URL:", self.repo_url_edit)
        
        repo_test_layout = QHBoxLayout()
        self.test_repo_btn = ModernButton("Test Connection")
        self.test_repo_btn.clicked.connect(self.test_repository)
        repo_test_layout.addWidget(self.test_repo_btn)
        repo_test_layout.addStretch()
        
        repository_form.addRow("", repo_test_layout)
        general_layout.addLayout(repository_form)
        
        # Minecraft settings
        minecraft_form = QFormLayout()
        minecraft_form.setSpacing(10)
        
        self.minecraft_dir_edit = ModernLineEdit()
        minecraft_form.addRow("Minecraft Directory:", self.minecraft_dir_edit)
        
        mc_dir_layout = QHBoxLayout()
        self.browse_mc_dir_btn = ModernButton("Browse...")
        self.browse_mc_dir_btn.clicked.connect(self.browse_minecraft_dir)
        mc_dir_layout.addWidget(self.browse_mc_dir_btn)
        mc_dir_layout.addStretch()
        
        minecraft_form.addRow("", mc_dir_layout)
        general_layout.addLayout(minecraft_form)
        
        # Update settings
        self.check_updates_cb = QCheckBox("Check for updates on startup")
        general_layout.addWidget(self.check_updates_cb)
        
        general_layout.addStretch(1)
        
        # Java settings tab
        self.java_tab = QWidget()
        java_layout = QVBoxLayout(self.java_tab)
        java_layout.setContentsMargins(20, 20, 20, 20)
        java_layout.setSpacing(15)
        
        # Java path
        java_form = QFormLayout()
        java_form.setSpacing(10)
        
        self.java_path_edit = ModernLineEdit()
        java_form.addRow("Java Path:", self.java_path_edit)
        
        java_path_layout = QHBoxLayout()
        self.browse_java_btn = ModernButton("Browse...")
        self.browse_java_btn.clicked.connect(self.browse_java_path)
        java_path_layout.addWidget(self.browse_java_btn)
        
        self.detect_java_btn = ModernButton("Auto-detect")
        self.detect_java_btn.clicked.connect(self.detect_java)
        java_path_layout.addWidget(self.detect_java_btn)
        
        java_path_layout.addStretch()
        
        java_form.addRow("", java_path_layout)
        
        # Java memory
        self.java_memory_edit = ModernLineEdit(placeholder="2G")
        java_form.addRow("Memory Allocation:", self.java_memory_edit)
        
        # Java arguments
        self.java_args_edit = ModernLineEdit(placeholder="-XX:+UseG1GC")
        java_form.addRow("Additional Arguments:", self.java_args_edit)
        
        java_layout.addLayout(java_form)
        java_layout.addStretch(1)
        
        # Add tabs
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.java_tab, "Java")
        
        layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        
        self.cancel_btn = ModernButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)
        
        self.save_btn = ModernButton("Save", True)
        self.save_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        
    def load_settings(self):
        """Load settings from config."""
        # Server URL
        server_url = self.config.get("server_url", "http://localhost:5000")
        self.repo_url_edit.setText(server_url)
        
        # Minecraft directory
        mc_dir = self.config.get("minecraft_directory", "")
        self.minecraft_dir_edit.setText(mc_dir)
        
        # Check for updates
        check_updates = self.config.get("check_for_updates", True)
        self.check_updates_cb.setChecked(check_updates)
        
        # Java settings
        java_path = self.config.get("java_path", "java")
        self.java_path_edit.setText(java_path)
        
        # Extract memory allocation from Java args
        java_args = self.config.get("java_args", "-Xmx2G")
        memory = "2G"
        args = []
        
        for arg in java_args.split():
            if arg.startswith("-Xmx"):
                memory = arg[4:]  # Remove "-Xmx" prefix
            else:
                args.append(arg)
                
        self.java_memory_edit.setText(memory)
        self.java_args_edit.setText(" ".join(args))
        
    def save_settings(self):
        """Save settings to config."""
        # Server URL
        server_url = self.repo_url_edit.text().strip()
        if server_url:
            self.config.set("server_url", server_url)
            
            # Update repository URLs
            repos = self.config.get("repositories", {})
            for repo_id, repo_info in repos.items():
                repo_info["url"] = server_url
            self.config.set("repositories", repos)
            
        # Minecraft directory
        mc_dir = self.minecraft_dir_edit.text().strip()
        if mc_dir:
            self.config.set("minecraft_directory", mc_dir)
            
        # Check for updates
        self.config.set("check_for_updates", self.check_updates_cb.isChecked())
        
        # Java settings
        java_path = self.java_path_edit.text().strip()
        if java_path:
            self.config.set("java_path", java_path)
            
        # Memory and Java args
        memory = self.java_memory_edit.text().strip()
        if not memory.startswith("-Xmx"):
            memory = f"-Xmx{memory}"
            
        args = self.java_args_edit.text().strip()
        java_args = memory
        if args:
            java_args = f"{memory} {args}"
            
        self.config.set("java_args", java_args)
        
        # Save all changes
        self.config.save()
        
    def accept(self):
        """Override accept to save settings."""
        self.save_settings()
        super().accept()
        
    def browse_minecraft_dir(self):
        """Browse for Minecraft directory."""
        from PyQt6.QtWidgets import QFileDialog
        
        current_dir = self.minecraft_dir_edit.text()
        if not current_dir:
            # Default to home directory
            from pathlib import Path
            current_dir = str(Path.home())
            
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Minecraft Directory",
            current_dir
        )
        
        if directory:
            self.minecraft_dir_edit.setText(directory)
            
    def browse_java_path(self):
        """Browse for Java executable."""
        from PyQt6.QtWidgets import QFileDialog
        
        current_path = self.java_path_edit.text()
        current_dir = os.path.dirname(current_path) if current_path else ""
        
        if not current_dir:
            # Default to a common location
            if os.name == "nt":  # Windows
                current_dir = "C:\\Program Files\\Java"
            else:
                current_dir = "/usr/bin"
                
        file_filter = "Java Executable (java.exe)" if os.name == "nt" else "Java Executable (java)"
        
        java_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Java Executable",
            current_dir,
            file_filter
        )
        
        if java_path:
            self.java_path_edit.setText(java_path)
            
    def detect_java(self):
        """Auto-detect Java installation."""
        try:
            import subprocess
            
            # Try to run java -version
            if os.name == "nt":  # Windows
                proc = subprocess.run(["where", "java"], capture_output=True, text=True, check=False)
                if proc.returncode == 0 and proc.stdout.strip():
                    java_path = proc.stdout.splitlines()[0].strip()
                    self.java_path_edit.setText(java_path)
                    QMessageBox.information(self, "Java Detected", f"Found Java at: {java_path}")
                    return
            else:
                proc = subprocess.run(["which", "java"], capture_output=True, text=True, check=False)
                if proc.returncode == 0 and proc.stdout.strip():
                    java_path = proc.stdout.strip()
                    self.java_path_edit.setText(java_path)
                    QMessageBox.information(self, "Java Detected", f"Found Java at: {java_path}")
                    return
                    
            # If we get here, no Java was found
            QMessageBox.warning(self, "Java Not Found", "Could not automatically detect Java installation.")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error detecting Java: {str(e)}")
            
    def test_repository(self):
        """Test connection to the repository."""
        url = self.repo_url_edit.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a repository URL.")
            return
            
        try:
            import requests
            
            # Make sure the URL has http:// or https:// prefix
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
                self.repo_url_edit.setText(url)
                
            # Try to connect to the API endpoint
            api_url = f"{url}/api/modpacks"
            
            self.test_repo_btn.setEnabled(False)
            self.test_repo_btn.setText("Testing...")
            
            response = requests.get(api_url, timeout=5)
            
            self.test_repo_btn.setEnabled(True)
            self.test_repo_btn.setText("Test Connection")
            
            # Check response
            if response.status_code == 200:
                try:
                    modpacks = response.json()
                    QMessageBox.information(
                        self, 
                        "Connection Successful", 
                        f"Successfully connected to the repository. Found {len(modpacks)} modpacks."
                    )
                except Exception:
                    QMessageBox.information(
                        self, 
                        "Connection Successful", 
                        "Successfully connected to the repository, but could not parse the response."
                    )
            else:
                QMessageBox.warning(
                    self, 
                    "Connection Failed", 
                    f"Could not connect to the repository. Status code: {response.status_code}"
                )
                
        except requests.exceptions.ConnectTimeout:
            self.test_repo_btn.setEnabled(True)
            self.test_repo_btn.setText("Test Connection")
            QMessageBox.warning(self, "Connection Timeout", "Connection to the repository timed out.")
            
        except requests.exceptions.ConnectionError:
            self.test_repo_btn.setEnabled(True)
            self.test_repo_btn.setText("Test Connection")
            QMessageBox.warning(self, "Connection Error", "Could not connect to the repository.")
            
        except Exception as e:
            self.test_repo_btn.setEnabled(True)
            self.test_repo_btn.setText("Test Connection")
            QMessageBox.warning(self, "Error", f"Error testing repository: {str(e)}")