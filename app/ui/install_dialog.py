#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installation dialog for Java and Minecraft.
"""

import os
import logging
import platform
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, 
    QPushButton, QProgressBar, QComboBox, QCheckBox, QListWidget, 
    QListWidgetItem, QGroupBox, QRadioButton, QButtonGroup, QSpacerItem,
    QSizePolicy, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread
from PyQt6.QtGui import QIcon, QFont

from app.core.java_installer import JavaInstaller
from app.core.minecraft_downloader import MinecraftDownloader


class JavaInstallThread(QThread):
    """Thread for installing Java."""
    
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(bool, object)
    
    def __init__(self, installer):
        """Initialize thread.
        
        Args:
            installer: JavaInstaller instance.
        """
        super().__init__()
        self.installer = installer
        
    def run(self):
        """Run the installation process."""
        try:
            result = self.installer.download_and_install_java(
                progress_callback=self.progress.emit
            )
            
            self.finished.emit(bool(result), result)
            
        except Exception as e:
            logging.error(f"Error in Java installation thread: {e}")
            self.progress.emit(1.0, f"Error: {str(e)}")
            self.finished.emit(False, str(e))


class MinecraftInstallThread(QThread):
    """Thread for installing Minecraft."""
    
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, downloader, version_id):
        """Initialize thread.
        
        Args:
            downloader: MinecraftDownloader instance.
            version_id: Minecraft version ID.
        """
        super().__init__()
        self.downloader = downloader
        self.version_id = version_id
        
    def run(self):
        """Run the installation process."""
        try:
            result = self.downloader.download_version(
                self.version_id,
                progress_callback=self.progress.emit
            )
            
            self.finished.emit(result, self.version_id)
            
        except Exception as e:
            logging.error(f"Error in Minecraft installation thread: {e}")
            self.progress.emit(1.0, f"Error: {str(e)}")
            self.finished.emit(False, str(e))


class InstallDialog(QDialog):
    """Dialog for installing Java and Minecraft."""
    
    installation_complete = pyqtSignal()
    
    def __init__(self, config, parent=None):
        """Initialize dialog.
        
        Args:
            config: Configuration instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config = config
        self.java_installer = JavaInstaller(config)
        self.minecraft_downloader = MinecraftDownloader(config)
        
        self.java_install_thread = None
        self.minecraft_install_thread = None
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("Installation Manager")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Java tab
        self.java_tab = QWidget()
        java_layout = QVBoxLayout(self.java_tab)
        
        # Java installations group
        java_group = QGroupBox("Installed Java Versions")
        java_group_layout = QVBoxLayout(java_group)
        
        # Java list
        self.java_list = QListWidget()
        java_group_layout.addWidget(self.java_list)
        
        # Java actions
        java_actions_layout = QHBoxLayout()
        
        self.detect_java_btn = QPushButton("Detect Java")
        self.detect_java_btn.clicked.connect(self.detect_java)
        java_actions_layout.addWidget(self.detect_java_btn)
        
        self.install_java_btn = QPushButton("Install Java 21")
        self.install_java_btn.clicked.connect(self.install_java)
        java_actions_layout.addWidget(self.install_java_btn)
        
        self.browse_java_btn = QPushButton("Browse...")
        self.browse_java_btn.clicked.connect(self.browse_java)
        java_actions_layout.addWidget(self.browse_java_btn)
        
        java_group_layout.addLayout(java_actions_layout)
        
        java_layout.addWidget(java_group)
        
        # Java progress
        self.java_progress_frame = QFrame()
        self.java_progress_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.java_progress_frame.setVisible(False)
        java_progress_layout = QVBoxLayout(self.java_progress_frame)
        
        self.java_progress_label = QLabel("Installing Java...")
        java_progress_layout.addWidget(self.java_progress_label)
        
        self.java_progress_bar = QProgressBar()
        java_progress_layout.addWidget(self.java_progress_bar)
        
        java_layout.addWidget(self.java_progress_frame)
        
        # Minecraft tab
        self.minecraft_tab = QWidget()
        minecraft_layout = QVBoxLayout(self.minecraft_tab)
        
        # Version selection
        version_group = QGroupBox("Minecraft Version")
        version_layout = QVBoxLayout(version_group)
        
        # Version filter
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.release_checkbox = QCheckBox("Release")
        self.release_checkbox.setChecked(True)
        self.release_checkbox.stateChanged.connect(self.filter_versions)
        filter_layout.addWidget(self.release_checkbox)
        
        self.snapshot_checkbox = QCheckBox("Snapshot")
        self.snapshot_checkbox.stateChanged.connect(self.filter_versions)
        filter_layout.addWidget(self.snapshot_checkbox)
        
        self.alpha_checkbox = QCheckBox("Alpha/Beta")
        self.alpha_checkbox.stateChanged.connect(self.filter_versions)
        filter_layout.addWidget(self.alpha_checkbox)
        
        filter_layout.addStretch()
        
        self.refresh_versions_btn = QPushButton("Refresh")
        self.refresh_versions_btn.clicked.connect(lambda: self.load_minecraft_versions(True))
        filter_layout.addWidget(self.refresh_versions_btn)
        
        version_layout.addLayout(filter_layout)
        
        # Version list
        self.version_list = QListWidget()
        self.version_list.currentItemChanged.connect(self.on_version_selected)
        version_layout.addWidget(self.version_list)
        
        minecraft_layout.addWidget(version_group)
        
        # Installation actions
        install_layout = QHBoxLayout()
        
        install_layout.addStretch()
        
        self.install_mc_btn = QPushButton("Install")
        self.install_mc_btn.setEnabled(False)
        self.install_mc_btn.clicked.connect(self.install_minecraft)
        install_layout.addWidget(self.install_mc_btn)
        
        minecraft_layout.addLayout(install_layout)
        
        # Minecraft progress
        self.mc_progress_frame = QFrame()
        self.mc_progress_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.mc_progress_frame.setVisible(False)
        mc_progress_layout = QVBoxLayout(self.mc_progress_frame)
        
        self.mc_progress_label = QLabel("Installing Minecraft...")
        mc_progress_layout.addWidget(self.mc_progress_label)
        
        self.mc_progress_bar = QProgressBar()
        mc_progress_layout.addWidget(self.mc_progress_bar)
        
        minecraft_layout.addWidget(self.mc_progress_frame)
        
        # Add tabs
        self.tab_widget.addTab(self.java_tab, "Java")
        self.tab_widget.addTab(self.minecraft_tab, "Minecraft")
        
        layout.addWidget(self.tab_widget, 1)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        
        buttons_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
    def load_data(self):
        """Load data for the dialog."""
        self.load_java_installations()
        self.load_minecraft_versions()
        
    def load_java_installations(self):
        """Load Java installations."""
        self.java_list.clear()
        
        java_versions = self.java_installer.get_installed_java_versions()
        
        for java in java_versions:
            version = java.get("version", "Unknown")
            vendor = java.get("vendor", "Unknown")
            path = java.get("path", "")
            is_system = java.get("system", False)
            
            item = QListWidgetItem(f"{vendor} {version}")
            
            # Add tooltip with path
            item.setToolTip(f"Path: {path}")
            
            # Set data
            item.setData(Qt.ItemDataRole.UserRole, java)
            
            # Mark current Java
            current_java = self.config.get("java_path", "")
            if current_java and path == current_java:
                item.setText(f"{vendor} {version} (Current)")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
            self.java_list.addItem(item)
            
    def load_minecraft_versions(self, force_refresh=False):
        """Load Minecraft versions.
        
        Args:
            force_refresh (bool): Force refresh from remote.
        """
        self.version_list.clear()
        self.refresh_versions_btn.setEnabled(False)
        self.refresh_versions_btn.setText("Refreshing...")
        
        # Get versions in background
        # In a real implementation, this would be done in a separate thread
        versions = self.minecraft_downloader.get_available_versions()
        installed_versions = self.minecraft_downloader.get_installed_versions()
        
        # Filter versions
        self.filter_versions()
        
        self.refresh_versions_btn.setEnabled(True)
        self.refresh_versions_btn.setText("Refresh")
        
    def filter_versions(self):
        """Filter Minecraft versions based on checkboxes."""
        self.version_list.clear()
        
        # Get filters
        show_release = self.release_checkbox.isChecked()
        show_snapshot = self.snapshot_checkbox.isChecked()
        show_old = self.alpha_checkbox.isChecked()
        
        # Get versions
        versions = self.minecraft_downloader.get_available_versions()
        installed_versions = self.minecraft_downloader.get_installed_versions()
        
        # Add filtered versions
        for version in versions:
            version_id = version.get("id", "")
            version_type = version.get("type", "")
            
            # Apply filters
            if (version_type == "release" and not show_release) or \
               (version_type == "snapshot" and not show_snapshot) or \
               (version_type in ["old_alpha", "old_beta"] and not show_old):
                continue
                
            item = QListWidgetItem(version_id)
            item.setData(Qt.ItemDataRole.UserRole, version)
            
            # Check if installed
            if version_id in installed_versions:
                item.setText(f"{version_id} (Installed)")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
            self.version_list.addItem(item)
            
    def on_version_selected(self, current, previous):
        """Handle version selection.
        
        Args:
            current (QListWidgetItem): Current item.
            previous (QListWidgetItem): Previous item.
        """
        if not current:
            self.install_mc_btn.setEnabled(False)
            return
            
        version = current.data(Qt.ItemDataRole.UserRole)
        version_id = version.get("id", "")
        
        # Check if already installed
        if self.minecraft_downloader.is_version_installed(version_id):
            self.install_mc_btn.setText("Reinstall")
        else:
            self.install_mc_btn.setText("Install")
            
        self.install_mc_btn.setEnabled(True)
        
    def detect_java(self):
        """Detect Java installations."""
        # Re-scan for Java
        self.load_java_installations()
        
    def browse_java(self):
        """Browse for Java installation."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Determine file filter based on OS
        if platform.system() == "Windows":
            file_filter = "Java Executable (javaw.exe)"
            default_dir = "C:\\Program Files\\Java"
        else:
            file_filter = "Java Executable (java)"
            default_dir = "/usr/lib/jvm"
            
        java_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Java Executable",
            default_dir,
            file_filter
        )
        
        if java_path:
            # Verify it's a valid Java
            version_info = self.java_installer._get_java_version(java_path)
            if version_info:
                # Add to config
                self.config.set("java_path", java_path)
                self.config.save()
                
                # Refresh list
                self.load_java_installations()
                
                QMessageBox.information(
                    self,
                    "Java Added",
                    f"Java {version_info.get('version')} has been set as the current Java."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Java",
                    "The selected file is not a valid Java executable."
                )
                
    def install_java(self):
        """Install Java 21."""
        # Disable UI
        self.setEnabled(False)
        self.java_progress_frame.setVisible(True)
        self.java_progress_label.setText("Preparing to install Java 21...")
        self.java_progress_bar.setValue(0)
        
        # Start installation thread
        self.java_install_thread = JavaInstallThread(self.java_installer)
        self.java_install_thread.progress.connect(self.update_java_progress)
        self.java_install_thread.finished.connect(self.java_installation_finished)
        self.java_install_thread.start()
        
    @pyqtSlot(float, str)
    def update_java_progress(self, progress, status):
        """Update Java installation progress.
        
        Args:
            progress (float): Progress value (0.0 to 1.0).
            status (str): Status message.
        """
        self.java_progress_bar.setValue(int(progress * 100))
        self.java_progress_label.setText(status)
        
    @pyqtSlot(bool, object)
    def java_installation_finished(self, success, result):
        """Handle Java installation completion.
        
        Args:
            success (bool): Whether installation was successful.
            result: Installation result.
        """
        # Re-enable UI
        self.setEnabled(True)
        self.java_progress_frame.setVisible(False)
        
        if success:
            if isinstance(result, dict) and result.get("needs_manual_install"):
                # Manual installation required
                QMessageBox.information(
                    self,
                    "Manual Installation Required",
                    "The Java installer has been downloaded. Please run it manually to complete installation."
                )
            else:
                QMessageBox.information(
                    self,
                    "Java Installation Complete",
                    "Java 21 has been installed successfully and set as the current Java."
                )
                
            # Refresh list
            self.load_java_installations()
        else:
            QMessageBox.warning(
                self,
                "Java Installation Failed",
                f"Failed to install Java 21: {result if isinstance(result, str) else 'Unknown error'}"
            )
            
    def install_minecraft(self):
        """Install selected Minecraft version."""
        current_item = self.version_list.currentItem()
        if not current_item:
            return
            
        version = current_item.data(Qt.ItemDataRole.UserRole)
        version_id = version.get("id", "")
        
        # Confirm reinstall if already installed
        if self.minecraft_downloader.is_version_installed(version_id):
            result = QMessageBox.question(
                self,
                "Confirm Reinstall",
                f"Minecraft {version_id} is already installed. Do you want to reinstall it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
                
        # Disable UI
        self.setEnabled(False)
        self.mc_progress_frame.setVisible(True)
        self.mc_progress_label.setText(f"Preparing to install Minecraft {version_id}...")
        self.mc_progress_bar.setValue(0)
        
        # Start installation thread
        self.minecraft_install_thread = MinecraftInstallThread(
            self.minecraft_downloader,
            version_id
        )
        self.minecraft_install_thread.progress.connect(self.update_minecraft_progress)
        self.minecraft_install_thread.finished.connect(self.minecraft_installation_finished)
        self.minecraft_install_thread.start()
        
    @pyqtSlot(float, str)
    def update_minecraft_progress(self, progress, status):
        """Update Minecraft installation progress.
        
        Args:
            progress (float): Progress value (0.0 to 1.0).
            status (str): Status message.
        """
        self.mc_progress_bar.setValue(int(progress * 100))
        self.mc_progress_label.setText(status)
        
    @pyqtSlot(bool, str)
    def minecraft_installation_finished(self, success, version_id):
        """Handle Minecraft installation completion.
        
        Args:
            success (bool): Whether installation was successful.
            version_id (str): Minecraft version ID.
        """
        # Re-enable UI
        self.setEnabled(True)
        self.mc_progress_frame.setVisible(False)
        
        if success:
            QMessageBox.information(
                self,
                "Installation Complete",
                f"Minecraft {version_id} has been installed successfully."
            )
            
            # Update version in config
            self.config.set("minecraft_version", version_id)
            self.config.save()
            
            # Refresh list
            self.load_minecraft_versions()
            
            # Emit signal
            self.installation_complete.emit()
        else:
            QMessageBox.warning(
                self,
                "Installation Failed",
                f"Failed to install Minecraft {version_id}"
            )