#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modpack browser for the Minecraft Modpack Launcher.
"""

import os
import logging
import tempfile
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QComboBox,
    QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QFrame, QSplitter, QCheckBox,
    QTabWidget, QTextEdit, QSpacerItem, QSizePolicy,
    QFileDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot, QDir
from PyQt6.QtGui import QIcon, QPixmap, QFont

from app.core.repository import RepositoryManager
from app.core.modpack import ModpackManager, Modpack


class DownloadThread(QThread):
    """Thread for downloading modpacks."""
    
    progress = pyqtSignal(float)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, repo_manager, repo_id, modpack_id, target_path):
        """Initialize download thread.
        
        Args:
            repo_manager: RepositoryManager instance.
            repo_id (str): Repository ID.
            modpack_id (str): Modpack ID.
            target_path (str): Path to save downloaded modpack.
        """
        super().__init__()
        self.repo_manager = repo_manager
        self.repo_id = repo_id
        self.modpack_id = modpack_id
        self.target_path = target_path
        
    def run(self):
        """Download modpack and emit results."""
        try:
            success = self.repo_manager.download_modpack(
                self.repo_id, 
                self.modpack_id, 
                self.target_path,
                self.progress.emit
            )
            
            self.finished.emit(success, self.target_path)
            
        except Exception as e:
            logging.error(f"Error in download thread: {e}")
            self.finished.emit(False, str(e))


class ModpackBrowserDialog(QDialog):
    """Dialog for browsing and installing modpacks."""
    
    modpack_installed = pyqtSignal(Modpack)
    
    def __init__(self, config, repo_manager, modpack_manager, parent=None):
        """Initialize modpack browser dialog.
        
        Args:
            config: Configuration instance.
            repo_manager: RepositoryManager instance.
            modpack_manager: ModpackManager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config = config
        self.repo_manager = repo_manager
        self.modpack_manager = modpack_manager
        self.selected_modpack = None
        self.download_thread = None
        
        self.init_ui()
        self.load_minecraft_versions()
        self.update_repositories()
        
    def init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("Browse Modpacks")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Search area
        search_frame = QFrame()
        search_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")
        search_layout = QHBoxLayout(search_frame)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search modpacks...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_edit)
        
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(120)
        self.version_combo.addItem("All Versions", None)
        self.version_combo.currentIndexChanged.connect(self.on_version_changed)
        search_layout.addWidget(QLabel("Minecraft:"))
        search_layout.addWidget(self.version_combo)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_modpacks)
        search_layout.addWidget(self.search_btn)
        
        layout.addWidget(search_frame)
        
        # Repository selection
        repo_frame = QFrame()
        repo_layout = QHBoxLayout(repo_frame)
        
        repo_layout.addWidget(QLabel("Repositories:"))
        
        # Add checkboxes for repositories
        self.repo_checkboxes = {}
        self.update_repo_btn = QPushButton("Update")
        self.update_repo_btn.clicked.connect(self.update_repositories)
        repo_layout.addWidget(self.update_repo_btn)
        repo_layout.addStretch()
        
        layout.addWidget(repo_frame)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Modpack list
        list_frame = QFrame()
        list_layout = QVBoxLayout(list_frame)
        
        self.modpack_list = QListWidget()
        self.modpack_list.setIconSize(QSize(64, 64))
        self.modpack_list.currentItemChanged.connect(self.on_modpack_selected)
        list_layout.addWidget(self.modpack_list)
        
        # Status label
        self.status_label = QLabel("Ready")
        list_layout.addWidget(self.status_label)
        
        content_splitter.addWidget(list_frame)
        
        # Modpack details
        details_frame = QFrame()
        details_layout = QVBoxLayout(details_frame)
        
        # Title and author
        title_layout = QVBoxLayout()
        
        self.title_label = QLabel("Select a modpack")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        self.author_label = QLabel("")
        self.author_label.setStyleSheet("font-size: 12px; color: #666;")
        title_layout.addWidget(self.author_label)
        
        details_layout.addLayout(title_layout)
        
        # Minecraft versions
        version_layout = QHBoxLayout()
        
        version_layout.addWidget(QLabel("Minecraft versions:"))
        
        self.versions_label = QLabel("")
        self.versions_label.setStyleSheet("font-weight: bold;")
        version_layout.addWidget(self.versions_label)
        
        version_layout.addStretch()
        
        details_layout.addLayout(version_layout)
        
        # Tabs for different sections
        self.detail_tabs = QTabWidget()
        
        # Description tab
        description_tab = QWidget()
        description_layout = QVBoxLayout(description_tab)
        
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        description_layout.addWidget(self.description_text)
        
        self.detail_tabs.addTab(description_tab, "Description")
        
        # Mods tab
        mods_tab = QWidget()
        mods_layout = QVBoxLayout(mods_tab)
        
        self.mods_list = QListWidget()
        mods_layout.addWidget(self.mods_list)
        
        self.detail_tabs.addTab(mods_tab, "Mods")
        
        # Screenshots tab
        screenshots_tab = QWidget()
        screenshots_layout = QVBoxLayout(screenshots_tab)
        
        self.screenshots_label = QLabel("No screenshots available")
        self.screenshots_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screenshots_layout.addWidget(self.screenshots_label)
        
        self.detail_tabs.addTab(screenshots_tab, "Screenshots")
        
        details_layout.addWidget(self.detail_tabs)
        
        # Install button
        self.install_btn = QPushButton("Install Modpack")
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ECC71;
            }
            QPushButton:pressed {
                background-color: #239A55;
            }
            QPushButton:disabled {
                background-color: #95A5A6;
            }
        """)
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self.install_modpack)
        details_layout.addWidget(self.install_btn)
        
        content_splitter.addWidget(details_frame)
        content_splitter.setSizes([300, 600])
        
        layout.addWidget(content_splitter)
        
        # Progress bar (hidden by default)
        self.progress_frame = QFrame()
        progress_layout = QVBoxLayout(self.progress_frame)
        
        self.progress_label = QLabel("Downloading modpack...")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_frame.setVisible(False)
        layout.addWidget(self.progress_frame)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("Import Local Modpack")
        self.import_btn.clicked.connect(self.import_modpack)
        buttons_layout.addWidget(self.import_btn)
        
        buttons_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
    def load_minecraft_versions(self):
        """Load Minecraft versions into the combo box."""
        # Get current Minecraft version
        current_version = self.config.get("minecraft_version", "1.19.4")
        
        # Add common versions
        versions = ["1.20.2", "1.19.4", "1.18.2", "1.16.5", "1.12.2", "1.7.10"]
        
        # Ensure current version is in the list
        if current_version not in versions:
            versions.append(current_version)
            
        versions.sort(reverse=True)
        
        # Add versions to combo box
        for version in versions:
            self.version_combo.addItem(version, version)
            
        # Set current version
        index = self.version_combo.findData(current_version)
        if index >= 0:
            self.version_combo.setCurrentIndex(index)
            
    def update_repositories(self):
        """Update repository checkboxes and refresh modpacks."""
        # Clear existing checkboxes
        for checkbox in self.repo_checkboxes.values():
            checkbox.setParent(None)
            
        self.repo_checkboxes = {}
        
        # Add checkboxes for repositories
        repo_layout = self.findChild(QFrame, None, Qt.FindChildOption.FindDirectChildrenOnly).layout()
        
        # Find the position to insert checkboxes (after "Repositories:" label)
        insert_pos = 1
        
        for repo_id, repo in self.repo_manager.repositories.items():
            checkbox = QCheckBox(repo.name)
            checkbox.setChecked(repo.enabled)
            checkbox.stateChanged.connect(lambda state, r=repo_id: self.on_repo_toggled(r, state))
            
            self.repo_checkboxes[repo_id] = checkbox
            repo_layout.insertWidget(insert_pos, checkbox)
            insert_pos += 1
            
        # Update repositories in background
        self.update_repo_btn.setEnabled(False)
        self.update_repo_btn.setText("Updating...")
        
        # In a real implementation, this would be done in a separate thread
        results = self.repo_manager.update_all_repositories()
        
        self.update_repo_btn.setEnabled(True)
        self.update_repo_btn.setText("Update")
        
        # Refresh modpack list
        self.search_modpacks()
        
    def on_repo_toggled(self, repo_id, state):
        """Handle repository checkbox toggle.
        
        Args:
            repo_id (str): Repository ID.
            state (int): Checkbox state.
        """
        repo = self.repo_manager.get_repository(repo_id)
        if repo:
            repo.enabled = state == Qt.CheckState.Checked.value
            self.search_modpacks()
            
    def on_search_changed(self, text):
        """Handle search text change.
        
        Args:
            text (str): Search text.
        """
        # Auto-search after typing
        self.search_modpacks()
        
    def on_version_changed(self, index):
        """Handle version combo box change.
        
        Args:
            index (int): Selected index.
        """
        # Auto-search after changing version
        self.search_modpacks()
        
    def search_modpacks(self):
        """Search for modpacks and update the list."""
        self.modpack_list.clear()
        self.selected_modpack = None
        self.clear_modpack_details()
        
        # Get search parameters
        query = self.search_edit.text()
        mc_version = self.version_combo.currentData()
        
        # Update status
        self.status_label.setText("Searching...")
        
        # Search for modpacks
        modpacks = self.repo_manager.search_modpacks(query, mc_version)
        
        # Update list
        for modpack in modpacks:
            item = QListWidgetItem(modpack.get("name", "Unknown"))
            item.setData(Qt.ItemDataRole.UserRole, modpack)
            
            # In a real implementation, load actual modpack icons
            # item.setIcon(QIcon(modpack_icon_path))
            
            self.modpack_list.addItem(item)
            
        # Update status
        if modpacks:
            self.status_label.setText(f"Found {len(modpacks)} modpacks")
        else:
            self.status_label.setText("No modpacks found")
            
    def on_modpack_selected(self, current, previous):
        """Handle modpack selection change.
        
        Args:
            current (QListWidgetItem): Current item.
            previous (QListWidgetItem): Previous item.
        """
        if not current:
            self.clear_modpack_details()
            self.selected_modpack = None
            self.install_btn.setEnabled(False)
            return
            
        # Get modpack data
        modpack_data = current.data(Qt.ItemDataRole.UserRole)
        self.selected_modpack = modpack_data
        
        # Update details
        self.title_label.setText(modpack_data.get("name", "Unknown"))
        self.author_label.setText(f"by {modpack_data.get('author', 'Unknown')}")
        self.versions_label.setText(", ".join(modpack_data.get("mc_versions", [])))
        self.description_text.setText(modpack_data.get("description", "No description available"))
        
        # Update mods list
        self.mods_list.clear()
        for mod in modpack_data.get("mods", []):
            mod_name = mod.get("name", "Unknown Mod")
            mod_version = mod.get("version", "Unknown Version")
            item = QListWidgetItem(f"{mod_name} v{mod_version}")
            self.mods_list.addItem(item)
            
        # Update screenshots (if available)
        # In a real implementation, load actual screenshots
        
        # Enable install button
        self.install_btn.setEnabled(True)
        
    def clear_modpack_details(self):
        """Clear modpack details."""
        self.title_label.setText("Select a modpack")
        self.author_label.setText("")
        self.versions_label.setText("")
        self.description_text.setText("")
        self.mods_list.clear()
        self.install_btn.setEnabled(False)
        
    def install_modpack(self):
        """Install selected modpack."""
        if not self.selected_modpack:
            return
            
        # Get modpack info
        modpack_name = self.selected_modpack.get("name", "Unknown")
        repo_id = self.selected_modpack.get("repository", {}).get("id")
        modpack_id = self.selected_modpack.get("id")
        
        if not repo_id or not modpack_id:
            QMessageBox.warning(
                self,
                "Installation Error",
                f"Cannot install modpack {modpack_name}: missing repository or modpack ID"
            )
            return
            
        # Confirm installation
        result = QMessageBox.question(
            self,
            "Install Modpack",
            f"Do you want to install {modpack_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result != QMessageBox.StandardButton.Yes:
            return
            
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            tmp_path = tmp_file.name
            
        # Show progress
        self.progress_frame.setVisible(True)
        self.progress_label.setText(f"Downloading {modpack_name}...")
        self.progress_bar.setValue(0)
        
        # Disable UI elements during download
        self.setEnabled(False)
        
        # Start download thread
        self.download_thread = DownloadThread(
            self.repo_manager,
            repo_id,
            modpack_id,
            tmp_path
        )
        
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()
        
    @pyqtSlot(float)
    def update_progress(self, progress):
        """Update progress bar.
        
        Args:
            progress (float): Progress value (0.0 to 1.0).
        """
        self.progress_bar.setValue(int(progress * 100))
        
    @pyqtSlot(bool, str)
    def download_finished(self, success, path_or_error):
        """Handle download completion.
        
        Args:
            success (bool): Whether download was successful.
            path_or_error (str): Path to downloaded file or error message.
        """
        self.setEnabled(True)
        self.progress_frame.setVisible(False)
        
        if not success:
            QMessageBox.warning(
                self,
                "Download Failed",
                f"Failed to download modpack: {path_or_error}"
            )
            return
            
        # Install modpack
        modpack = self.modpack_manager.install_modpack(path_or_error)
        
        # Clean up temporary file
        try:
            os.remove(path_or_error)
        except Exception as e:
            logging.warning(f"Failed to remove temporary file {path_or_error}: {e}")
            
        if modpack:
            QMessageBox.information(
                self,
                "Installation Successful",
                f"Modpack {modpack.name} installed successfully."
            )
            
            # Emit signal
            self.modpack_installed.emit(modpack)
            
            # Close dialog
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Installation Failed",
                "Failed to install modpack."
            )
            
    def import_modpack(self):
        """Import local modpack file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Modpack",
            "",
            "ZIP files (*.zip)"
        )
        
        if not file_path:
            return
            
        # Install modpack
        modpack = self.modpack_manager.install_modpack(file_path)
        
        if modpack:
            QMessageBox.information(
                self,
                "Import Successful",
                f"Modpack {modpack.name} imported successfully."
            )
            
            # Emit signal
            self.modpack_installed.emit(modpack)
            
            # Close dialog
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Import Failed",
                "Failed to import modpack."
            )