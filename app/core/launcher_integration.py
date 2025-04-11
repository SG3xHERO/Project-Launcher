#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minecraft launcher integration using minecraft-launcher-lib.
"""

import os
import sys
import json
import logging
import platform
import subprocess
import time
import threading
from typing import Dict, Any, Optional, List, Callable

import minecraft_launcher_lib


class MinecraftLauncher:
    """Manages Minecraft game instance using minecraft-launcher-lib."""
    
    def __init__(self, config, auth_manager):
        """Initialize Minecraft launcher.
        
        Args:
            config: Configuration instance.
            auth_manager: Authentication manager instance.
        """
        self.config = config
        self.auth_manager = auth_manager
        self.minecraft_dir = config.get("minecraft_directory")
        self.java_path = config.get("java_path", "")
        self.java_args = config.get("java_args", "-Xmx2G")
        
        # Ensure Minecraft directory exists
        os.makedirs(self.minecraft_dir, exist_ok=True)
        
        # Check if we need to use a custom Java installation
        if self.java_path and os.path.exists(self.java_path):
            minecraft_launcher_lib.utils.get_java_executable = lambda: self.java_path
    
    def get_versions(self) -> List[Dict[str, Any]]:
        """Get available Minecraft versions.
        
        Returns:
            List[Dict[str, Any]]: List of version information dictionaries.
        """
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            return versions
        except Exception as e:
            logging.error(f"Failed to get version list: {e}")
            return []
    
    def get_installed_versions(self) -> List[str]:
        """Get installed Minecraft versions.
        
        Returns:
            List[str]: List of installed version IDs.
        """
        try:
            versions = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
            return [version["id"] for version in versions]
        except Exception as e:
            logging.error(f"Failed to get installed versions: {e}")
            return []
    
    def is_version_installed(self, version_id: str) -> bool:
        """Check if a Minecraft version is installed.
        
        Args:
            version_id (str): Version ID to check.
            
        Returns:
            bool: True if version is installed, False otherwise.
        """
        return minecraft_launcher_lib.utils.is_version_valid(self.minecraft_dir, version_id)
    
    def install_minecraft_version(self, version_id: str, callback: Optional[Callable[[int, int, str], None]] = None) -> bool:
        """Install a Minecraft version.
        
        Args:
            version_id (str): Version ID to install.
            callback: Optional callback for progress updates.
            
        Returns:
            bool: True if installation was successful, False otherwise.
        """
        try:
            # Create a default callback if none provided
            if callback is None:
                def default_callback(current, total, status_text):
                    if total > 0:
                        progress = int((current / total) * 100)
                        logging.info(f"Installing Minecraft {version_id}: {progress}% - {status_text}")
                callback = default_callback
            
            # Install the version
            minecraft_launcher_lib.installer.install_minecraft_version(
                version_id, 
                self.minecraft_dir,
                callback=callback
            )
            
            logging.info(f"Successfully installed Minecraft {version_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to install Minecraft {version_id}: {e}")
            return False
    
    def install_forge_version(self, minecraft_version: str, forge_version: str, 
                             callback: Optional[Callable[[int, int, str], None]] = None) -> bool:
        """Install a Forge version.
        
        Args:
            minecraft_version (str): Minecraft version.
            forge_version (str): Forge version.
            callback: Optional callback for progress updates.
            
        Returns:
            bool: True if installation was successful, False otherwise.
        """
        try:
            # Create a default callback if none provided
            if callback is None:
                def default_callback(current, total, status_text):
                    if total > 0:
                        progress = int((current / total) * 100)
                        logging.info(f"Installing Forge {minecraft_version}-{forge_version}: {progress}% - {status_text}")
                callback = default_callback
            
            # Get the Forge version information
            forge_info = minecraft_launcher_lib.forge.find_forge_version(minecraft_version, forge_version)
            
            if not forge_info:
                logging.error(f"Forge version {forge_version} for Minecraft {minecraft_version} not found")
                return False
            
            # Install Forge
            minecraft_launcher_lib.forge.install_forge_version(
                forge_info["version"], 
                self.minecraft_dir,
                callback=callback
            )
            
            logging.info(f"Successfully installed Forge {forge_version} for Minecraft {minecraft_version}")
            return True
        except Exception as e:
            logging.error(f"Failed to install Forge: {e}")
            return False
    
    def install_fabric(self, minecraft_version: str, 
                      callback: Optional[Callable[[int, int, str], None]] = None) -> bool:
        """Install Fabric for a Minecraft version.
        
        Args:
            minecraft_version (str): Minecraft version.
            callback: Optional callback for progress updates.
            
        Returns:
            bool: True if installation was successful, False otherwise.
        """
        try:
            # Create a default callback if none provided
            if callback is None:
                def default_callback(current, total, status_text):
                    if total > 0:
                        progress = int((current / total) * 100)
                        logging.info(f"Installing Fabric for {minecraft_version}: {progress}% - {status_text}")
                callback = default_callback
            
            # Install Fabric
            minecraft_launcher_lib.fabric.install_fabric(
                minecraft_version, 
                self.minecraft_dir,
                callback=callback
            )
            
            logging.info(f"Successfully installed Fabric for Minecraft {minecraft_version}")
            return True
        except Exception as e:
            logging.error(f"Failed to install Fabric: {e}")
            return False
    
    def launch_minecraft(self, version_id: str, modpack_dir: Optional[str] = None,
                        custom_options: Optional[Dict[str, Any]] = None,
                        callback: Optional[Callable[[str], None]] = None) -> subprocess.Popen:
        """Launch Minecraft.
        
        Args:
            version_id (str): Minecraft version ID.
            modpack_dir (Optional[str]): Path to modpack directory.
            custom_options (Optional[Dict[str, Any]]): Custom launch options.
            callback (Optional[Callable[[str], None]]): Callback for log output.
            
        Returns:
            subprocess.Popen: Process object for the launched game.
        """
        # Verify authentication
        if not self.auth_manager.is_logged_in():
            raise ValueError("User is not authenticated. Please login first.")
        
        # Build options
        options = {
            # JVM arguments
            "jvmArguments": self.java_args.split(),
            
            # Resolution
            "resolutionWidth": "1280",
            "resolutionHeight": "720",
            
            # Game directory - use modpack directory if provided
            "gameDirectory": modpack_dir if modpack_dir else self.minecraft_dir,
            
            # Disable Forge's display dialog
            "launcherName": "Project Launcher",
            "launcherVersion": "1.0.0"
        }
        
        # Add custom options if provided
        if custom_options:
            options.update(custom_options)
        
        try:
            # Generate the command
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                version=version_id,
                minecraft_directory=self.minecraft_dir,
                options=options,
                username=self.auth_manager.get_username(),
                uuid=self.auth_manager.get_uuid(),
                token=self.auth_manager.auth_data.get("access_token")
            )
            
            logging.info(f"Launching Minecraft {version_id}")
            logging.debug(f"Command: {' '.join(minecraft_command)}")
            
            # Create process
            process = subprocess.Popen(
                minecraft_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Create thread to read and process output if callback provided
            if callback:
                def read_output():
                    for line in iter(process.stdout.readline, ""):
                        callback(line.strip())
                    process.stdout.close()
                
                def read_error():
                    for line in iter(process.stderr.readline, ""):
                        callback(f"ERROR: {line.strip()}")
                    process.stderr.close()
                
                threading.Thread(target=read_output, daemon=True).start()
                threading.Thread(target=read_error, daemon=True).start()
            
            return process
        
        except Exception as e:
            logging.error(f"Failed to launch Minecraft: {e}")
            raise