#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modpack manager UI component for the Minecraft Modpack Launcher.
"""

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTabWidget,
    QListWidget, QListWidgetItem, QMessageBox, 
    QProgressBar, QSplitter, QFrame, QFileDialog,
    QTextEdit, QGroupBox, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

from app.core.modpack_loader import Modpack
from app.core.mods import Mod


class ModpackManagerWidget(QWidget):
    """Widget for managing a modpack."""
    
    modpack_updated = pyqtSignal(Modpack)
    
    def __init__(self, config, modpack_manager, parent=None):
        """Initialize modpack manager widget.
        
        Args:
            config: Configuration instance.
            modpack_manager: ModpackManager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config = config
        self.modpack_manager = modpack_manager
        self.modpack = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Info area
        self.info_frame = QFrame()
        info_layout = QVBoxLayout(self.info_frame)
        
        # Title and description
        self.title_label = QLabel("Select a modpack")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        info_layout.addWidget(self.title_label)
        
        self.author_label = QLabel("")
        self.author_label.setStyleSheet("font-size: 12px; color: #666;")
        info_layout.addWidget(self.author_label)
        
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(100)
        info_layout.addWidget(self.description_text)
        
        # Compatibility info
        compatibility_layout = QHBoxLayout()
        
        self.version_label = QLabel("Minecraft versions: ")
        compatibility_layout.addWidget(self.version_label)
        
        self.compatibility_label = QLabel("")
        self.compatibility_label.setStyleSheet("font-weight: bold;")
        compatibility_layout.addWidget(self.compatibility_label)
        
        compatibility_layout.addStretch()
        
        self.mod_count_label = QLabel("Mods: 0")
        compatibility_layout.addWidget(self.mod_count_label)
        
        info_layout.addLayout(compatibility_layout)
        
        layout.addWidget(self.info_frame)
        
        # Tab widget for different sections
        self.tab_widget = QTabWidget()
        
        # Mods tab
        self.mods_tab = QWidget()
        mods_layout = QVBoxLayout(self.mods_tab)
        
        # Mod list
        self.mod_list = QListWidget()
        self.mod_list.setIconSize(QSize(32, 32))
        self.mod_list.itemClicked.connect(self.on_mod_selected)
        mods_layout.addWidget(self.mod_list)
        
        # Mod actions
        mod_actions_layout = QHBoxLayout()
        
        self.add_mod_btn = QPushButton("Add Mod")
        self.add_mod_btn.clicked.connect(self.add_mod)
        mod_actions_layout.addWidget(self.add_mod_btn)
        
        self.remove_mod_btn = QPushButton("Remove Mod")
        self.remove_mod_btn.clicked.connect(self.remove_mod)
        self.remove_mod_btn.setEnabled(False)
        mod_actions_layout.addWidget(self.remove_mod_btn)
        
        self.update_mod_btn = QPushButton("Update Mod")
        self.update_mod_btn.clicked.connect(self.update_mod)
        self.update_mod_btn.setEnabled(False)
        mod_actions_layout.addWidget(self.update_mod_btn)
        
        mods_layout.addLayout(mod_actions_layout)
        
        # Mod details
        self.mod_details = QLabel("Select a mod to view details")
        self.mod_details.setWordWrap(True)
        self.mod_details.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 4px;")
        self.mod_details.setMinimumHeight(100)
        mods_layout.addWidget(self.mod_details)
        
        # Config tab
        self.config_tab = QWidget()
        config_layout = QVBoxLayout(self.config_tab)
        
        # Config list
        self.config_list = QListWidget()
        config_layout.addWidget(self.config_list)
        
        # Config actions
        config_actions_layout = QHBoxLayout()
        
        self.edit_config_btn = QPushButton("Edit Config")
        config_actions_layout.addWidget(self.edit_config_btn)
        
        self.reset_config_btn = QPushButton("Reset to Default")
        config_actions_layout.addWidget(self.reset_config_btn)
        
        config_layout.addLayout(config_actions_layout)
        
        # Resource packs tab
        self.resource_tab = QWidget()
        resource_layout = QVBoxLayout(self.resource_tab)
        
        # Resource pack list
        self.resource_list = QListWidget()
        resource_layout.addWidget(self.resource_list)
        
        # Resource pack actions
        resource_actions_layout = QHBoxLayout()
        
        self.add_resource_btn = QPushButton("Add Resource Pack")
        resource_actions_layout.addWidget(self.add_resource_btn)
        
        self.remove_resource_btn = QPushButton("Remove Resource Pack")
        resource_actions_layout.addWidget(self.remove_resource_btn)
        
        resource_layout.addLayout(resource_actions_layout)
        
        # Settings tab
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        
        # Java settings group
        java_group = QGroupBox("Java Settings")
        java_layout = QFormLayout(java_group)
        
        # Memory allocation
        self.memory_spin = QSpinBox()
        self.memory_spin.setMinimum(1)
        self.memory_spin.setMaximum(32)
        self.memory_spin.setSuffix(" GB")
        self.memory_spin.setValue(2)
        java_layout.addRow("Memory Allocation:", self.memory_spin)
        
        # Java arguments
        self.java_args_edit = QTextEdit()
        self.java_args_edit.setMaximumHeight(80)
        self.java_args_edit.setPlaceholderText("Additional Java arguments")
        java_layout.addRow("Java Arguments:", self.java_args_edit)
        
        settings_layout.addWidget(java_group)
        
        # Modpack settings group
        modpack_group = QGroupBox("Modpack Settings")
        modpack_layout = QFormLayout(modpack_group)
        
        # TODO: Add modpack-specific settings
        modpack_layout.addRow("", QLabel("Modpack-specific settings will be added here"))
        
        settings_layout.addWidget(modpack_group)
        
        # Add tabs
        self.tab_widget.addTab(self.mods_tab, "Mods")
        self.tab_widget.addTab(self.config_tab, "Config")
        self.tab_widget.addTab(self.resource_tab, "Resource Packs")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        layout.addWidget(self.tab_widget)
        
        # Modpack actions
        actions_layout = QHBoxLayout()
        
        self.update_btn = QPushButton("Check for Updates")
        self.update_btn.clicked.connect(self.check_for_updates)
        actions_layout.addWidget(self.update_btn)
        
        self.export_btn = QPushButton("Export Modpack")
        self.export_btn.clicked.connect(self.export_modpack)
        actions_layout.addWidget(self.export_btn)
        
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.clicked.connect(self.uninstall_modpack)
        self.uninstall_btn.setStyleSheet("color: #e74c3c;")
        actions_layout.addWidget(self.uninstall_btn)
        
        layout.addLayout(actions_layout)
        
        # Disable all by default
        self.set_ui_enabled(False)
        
    def set_ui_enabled(self, enabled):
        """Enable or disable UI elements.
        
        Args:
            enabled (bool): Whether to enable UI elements.
        """
        self.add_mod_btn.setEnabled(enabled)
        self.update_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled)
        self.uninstall_btn.setEnabled(enabled)
        self.tab_widget.setEnabled(enabled)
        
    def set_modpack(self, modpack):
        """Set current modpack.
        
        Args:
            modpack (Modpack): Modpack to set.
        """
        self.modpack = modpack
        
        if modpack:
            self.title_label.setText(modpack.name)
            self.author_label.setText(f"by {modpack.author}")
            self.description_text.setText(modpack.description)
            self.version_label.setText(f"Minecraft versions: {', '.join(modpack.mc_versions)}")
            
            # Check compatibility with current Minecraft version
            current_mc_version = self.config.get("minecraft_version", "1.19.4")
            compatible = current_mc_version in modpack.mc_versions
            
            if compatible:
                self.compatibility_label.setText("Compatible")
                self.compatibility_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            else:
                self.compatibility_label.setText("Incompatible")
                self.compatibility_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                
            # Update mod count
            self.mod_count_label.setText(f"Mods: {len(modpack.mods)}")
            
            # Load mods
            self.load_mods()
            
            # Load configs
            self.load_configs()
            
            # Load resource packs
            self.load_resource_packs()
            
            # Enable UI
            self.set_ui_enabled(True)
        else:
            self.clear_modpack()
            
    def clear_modpack(self):
        """Clear current modpack."""
        self.modpack = None
        self.title_label.setText("Select a modpack")
        self.author_label.setText("")
        self.description_text.setText("")
        self.version_label.setText("Minecraft versions: ")
        self.compatibility_label.setText("")
        self.mod_count_label.setText("Mods: 0")
        
        # Clear lists
        self.mod_list.clear()
        self.config_list.clear()
        self.resource_list.clear()
        
        # Disable UI
        self.set_ui_enabled(False)
        self.remove_mod_btn.setEnabled(False)
        self.update_mod_btn.setEnabled(False)
        
    def load_mods(self):
        """Load mods from current modpack."""
        self.mod_list.clear()
        
        if not self.modpack:
            return
            
        for mod_info in self.modpack.mods:
            item = QListWidgetItem(mod_info.get("name", "Unknown Mod"))
            # In a real implementation, load actual mod icons
            # item.setIcon(QIcon(mod_icon_path))
            item.setData(Qt.ItemDataRole.UserRole, mod_info)
            self.mod_list.addItem(item)
            
    def load_configs(self):
        """Load configs from current modpack."""
        self.config_list.clear()
        
        if not self.modpack or not self.modpack.is_installed:
            return
            
        config_dir = os.path.join(self.modpack.install_path, "config")
        if not os.path.exists(config_dir):
            return
            
        for root, dirs, files in os.walk(config_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), config_dir)
                item = QListWidgetItem(rel_path)
                item.setData(Qt.ItemDataRole.UserRole, os.path.join(root, file))
                self.config_list.addItem(item)
                
    def load_resource_packs(self):
        """Load resource packs from current modpack."""
        self.resource_list.clear()
        
        if not self.modpack or not self.modpack.is_installed:
            return
            
        resource_dir = os.path.join(self.modpack.install_path, "resourcepacks")
        if not os.path.exists(resource_dir):
            return
            
        for file in os.listdir(resource_dir):
            item = QListWidgetItem(file)
            item.setData(Qt.ItemDataRole.UserRole, os.path.join(resource_dir, file))
            self.resource_list.addItem(item)
            
    def load_modpacks(self):
        """Load modpacks."""
        self.modpack_list.clear()
        self.modpack = None
        self.mod_list.clear()
        
        # Load installed modpacks
        installed_modpacks = self.modpack_manager.get_installed_modpacks()
        for modpack in installed_modpacks:
            self.add_modpack_to_list(modpack, is_installed=True)
        
        # Load server modpacks
        server_modpacks = self.modpack_manager.load_server_modpacks()
        for modpack in server_modpacks:
            # Check if this modpack is already installed
            is_installed = any(imp.id == modpack.id for imp in installed_modpacks)
            self.add_modpack_to_list(modpack, is_installed=is_installed)
        
        # Update counts
        self.modpack_count_label.setText(f"Modpacks: {self.modpack_list.count()}")
        
    def add_modpack_to_list(self, modpack, is_installed=False):
        """Add modpack to list."""
        item = QListWidgetItem()
        item.setText(f"{modpack.name} ({modpack.version})")
        item.setData(Qt.ItemDataRole.UserRole, modpack)
        
        if is_installed:
            item.setIcon(QIcon("icons/check.png"))  # Adjust icon path as needed
        elif modpack.is_server_pack:
            item.setIcon(QIcon("icons/download.png"))  # Adjust icon path as needed
        
        self.modpack_list.addItem(item)
        
    def on_mod_selected(self, item):
        """Handle mod selection.
        
        Args:
            item (QListWidgetItem): Selected item.
        """
        if not item:
            self.mod_details.setText("Select a mod to view details")
            self.remove_mod_btn.setEnabled(False)
            self.update_mod_btn.setEnabled(False)
            return
            
        mod_info = item.data(Qt.ItemDataRole.UserRole)
        
        # Build details text
        details = f"<b>{mod_info.get('name', 'Unknown Mod')}</b> v{mod_info.get('version', 'Unknown')}<br>"
        
        if mod_info.get('description'):
            details += f"{mod_info.get('description')}<br>"
            
        details += f"<br>Minecraft versions: {', '.join(mod_info.get('mc_versions', []))}"
        
        if mod_info.get('dependencies'):
            details += f"<br><br>Dependencies:<br>"
            for dep in mod_info.get('dependencies', []):
                details += f"• {dep}<br>"
                
        self.mod_details.setText(details)
        self.remove_mod_btn.setEnabled(True)
        self.update_mod_btn.setEnabled(True)
        
    def add_mod(self):
        """Add mod to modpack."""
        if not self.modpack:
            return
            
        # In a real implementation, this would open a dialog to search for mods
        # and select one to install
        QMessageBox.information(
            self,
            "Add Mod",
            "This would open a mod selection dialog to search for and add mods."
        )
        
    def remove_mod(self):
        """Remove selected mod from modpack."""
        if not self.modpack:
            return
            
        current_item = self.mod_list.currentItem()
        if not current_item:
            return
            
        mod_info = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Confirm removal
        result = QMessageBox.question(
            self,
            "Remove Mod",
            f"Are you sure you want to remove {mod_info.get('name', 'this mod')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            # Remove mod
            if self.modpack_manager.remove_mod_from_modpack(self.modpack, mod_info.get('id')):
                # Update UI
                self.load_mods()
                self.mod_count_label.setText(f"Mods: {len(self.modpack.mods)}")
                self.mod_details.setText("Select a mod to view details")
                self.remove_mod_btn.setEnabled(False)
                self.update_mod_btn.setEnabled(False)
                
                # Emit signal
                self.modpack_updated.emit(self.modpack)
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to remove {mod_info.get('name', 'mod')}."
                )
                
    def update_mod(self):
        """Update selected mod."""
        if not self.modpack:
            return
            
        current_item = self.mod_list.currentItem()
        if not current_item:
            return
            
        mod_info = current_item.data(Qt.ItemDataRole.UserRole)
        
        # In a real implementation, this would check for updates for the mod
        # and install them if available
        QMessageBox.information(
            self,
            "Update Mod",
            f"Checking for updates for {mod_info.get('name', 'this mod')}..."
        )
        
    def check_for_updates(self):
        """Check for modpack updates."""
        if not self.modpack:
            return
            
        # In a real implementation, this would check for updates for the modpack
        # and install them if available
        QMessageBox.information(
            self,
            "Check for Updates",
            f"Checking for updates for {self.modpack.name}..."
        )
        
    def export_modpack(self):
        """Export modpack to ZIP file."""
        if not self.modpack:
            return
            
        # Ask for export location
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Modpack",
            f"{self.modpack.name.replace(' ', '_')}.zip",
            "ZIP files (*.zip)"
        )
        
        if not export_path:
            return
            
        # Export modpack
        if self.modpack_manager.export_modpack(self.modpack, export_path):
            QMessageBox.information(
                self,
                "Export Successful",
                f"Modpack {self.modpack.name} exported to {export_path}."
            )
        else:
            QMessageBox.warning(
                self,
                "Export Failed",
                f"Failed to export modpack {self.modpack.name}."
            )
            
    def uninstall_modpack(self):
        """Uninstall modpack."""
        if not self.modpack:
            return
            
        # Confirm uninstallation
        result = QMessageBox.question(
            self,
            "Uninstall Modpack",
            f"Are you sure you want to uninstall {self.modpack.name}? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            # Uninstall modpack
            if self.modpack_manager.uninstall_modpack(self.modpack):
                # Clear UI
                self.clear_modpack()
                
                # Emit signal
                self.modpack_updated.emit(None)
                
                QMessageBox.information(
                    self,
                    "Uninstall Successful",
                    f"Modpack {self.modpack.name} uninstalled."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Uninstall Failed",
                    f"Failed to uninstall modpack {self.modpack.name}."
                )
                
    def refresh_compatibility(self):
        """Refresh compatibility status."""
        if not self.modpack:
            return
            
        # Check compatibility with current Minecraft version
        current_mc_version = self.config.get("minecraft_version", "1.19.4")
        compatible = current_mc_version in self.modpack.mc_versions
        
        if compatible:
            self.compatibility_label.setText("Compatible")
            self.compatibility_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.compatibility_label.setText("Incompatible")
            self.compatibility_label.setStyleSheet("color: #e74c3c; font-weight: bold;")