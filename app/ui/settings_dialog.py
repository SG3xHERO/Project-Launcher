#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings dialog for the Minecraft Modpack Launcher.
"""

import os
import logging
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QCheckBox,
    QSpinBox, QTabWidget, QFileDialog, QDialogButtonBox,
    QGroupBox, QFormLayout, QComboBox
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon, QFont

from app.utils import is_java_installed, get_memory_info, calculate_recommended_memory


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
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # General settings tab
        self.general_tab = QWidget()
        general_layout = QVBoxLayout(self.general_tab)
        
        # Minecraft directory
        mc_group = QGroupBox("Minecraft Directory")
        mc_layout = QHBoxLayout(mc_group)
        
        self.mc_dir_edit = QLineEdit()
        mc_layout.addWidget(self.mc_dir_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_minecraft_dir)
        mc_layout.addWidget(browse_btn)
        
        general_layout.addWidget(mc_group)
        
        # Java settings
        java_group = QGroupBox("Java Settings")
        java_layout = QFormLayout(java_group)
        
        # Java path
        self.java_path_edit = QLineEdit()
        java_layout.addRow("Java Path:", self.java_path_edit)
        
        # Java memory
        memory_layout = QHBoxLayout()
        self.memory_edit = QLineEdit()
        memory_layout.addWidget(self.memory_edit)
        
        detect_btn = QPushButton("Auto-detect")
        detect_btn.clicked.connect(self.auto_detect_memory)
        memory_layout.addWidget(detect_btn)
        
        java_layout.addRow("Memory Allocation:", memory_layout)
        
        # Java arguments
        self.java_args_edit = QLineEdit()
        java_layout.addRow("Additional Arguments:", self.java_args_edit)
        
        general_layout.addWidget(java_group)
        
        # Updates
        update_group = QGroupBox("Updates")
        update_layout = QVBoxLayout(update_group)
        
        self.check_updates_cb = QCheckBox("Check for updates on startup")
        update_layout.addWidget(self.check_updates_cb)
        
        self.check_modpack_updates_cb = QCheckBox("Check for modpack updates on startup")
        update_layout.addWidget(self.check_modpack_updates_cb)
        
        general_layout.addWidget(update_group)
        
        # Download settings tab
        self.download_tab = QWidget()
        download_layout = QVBoxLayout(self.download_tab)
        
        # Repository settings
        repo_group = QGroupBox("Modpack Repositories")
        repo_layout = QVBoxLayout(repo_group)
        
        # TODO: Add repository list widget
        repo_layout.addWidget(QLabel("Repository settings will be added here"))
        
        download_layout.addWidget(repo_group)
        
        # Download settings
        dl_group = QGroupBox("Download Settings")
        dl_layout = QFormLayout(dl_group)
        
        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setMinimum(1)
        self.max_threads_spin.setMaximum(16)
        dl_layout.addRow("Maximum download threads:", self.max_threads_spin)
        
        download_layout.addWidget(dl_group)
        
        # Add tabs
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.download_tab, "Downloads")
        
        layout.addWidget(self.tab_widget)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def load_settings(self):
        """Load settings from configuration."""
        # General settings
        self.mc_dir_edit.setText(self.config.get("minecraft_directory", ""))
        self.java_path_edit.setText(self.config.get("java_path", "java"))
        
        # Extract memory setting from Java args
        java_args = self.config.get("java_args", "-Xmx2G -XX:+UseG1GC")
        memory_setting = ""
        additional_args = []
        
        for arg in java_args.split():
            if arg.startswith("-Xmx"):
                memory_setting = arg[4:]  # Remove -Xmx prefix
            else:
                additional_args.append(arg)
                
        self.memory_edit.setText(memory_setting)
        self.java_args_edit.setText(" ".join(additional_args))
        
        # Update settings
        self.check_updates_cb.setChecked(self.config.get("check_for_updates", True))
        self.check_modpack_updates_cb.setChecked(self.config.get("check_for_modpack_updates", True))
        
        # Download settings
        self.max_threads_spin.setValue(self.config.get("max_download_threads", 3))
        
    def save_settings(self):
        """Save settings to configuration."""
        # General settings
        self.config.set("minecraft_directory", self.mc_dir_edit.text())
        self.config.set("java_path", self.java_path_edit.text())
        
        # Combine memory and additional args
        memory = self.memory_edit.text()
        if not memory.startswith("-Xmx"):
            memory = f"-Xmx{memory}"
            
        java_args = [memory] + self.java_args_edit.text().split()
        self.config.set("java_args", " ".join(java_args))
        
        # Update settings
        self.config.set("check_for_updates", self.check_updates_cb.isChecked())
        self.config.set("check_for_modpack_updates", self.check_modpack_updates_cb.isChecked())
        
        # Download settings
        self.config.set("max_download_threads", self.max_threads_spin.value())
        
        # Save configuration
        self.config.save()
        
    def accept(self):
        """Handle dialog acceptance."""
        self.save_settings()
        super().accept()
        
    def browse_minecraft_dir(self):
        """Open file dialog to browse for Minecraft directory."""
        current_dir = self.mc_dir_edit.text()
        if not current_dir or not os.path.exists(current_dir):
            current_dir = os.path.expanduser("~")
            
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Minecraft Directory",
            current_dir
        )
        
        if directory:
            self.mc_dir_edit.setText(directory)
            
    def auto_detect_memory(self):
        """Auto-detect recommended memory allocation."""
        memory_info = get_memory_info()
        recommended_memory = calculate_recommended_memory(memory_info)
        
        # Extract value from JVM format (e.g., "-Xmx4G" -> "4G")
        if recommended_memory.startswith("-Xmx"):
            recommended_memory = recommended_memory[4:]
            
        self.memory_edit.setText(recommended_memory)