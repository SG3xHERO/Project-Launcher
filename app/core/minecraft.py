#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minecraft instance management for the Minecraft Modpack Launcher.
"""

import os
import json
import logging
import platform
import subprocess
import time
import threading
from typing import Dict, Any, Optional, List, Callable

from app.utils import is_java_installed, get_memory_info, calculate_recommended_memory


class MinecraftInstance:
    """Manages Minecraft game instance."""
    
    def __init__(self, config):
        """Initialize Minecraft instance manager.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.minecraft_dir = config.get("minecraft_directory")
        self.java_path = config.get("java_path", "java")
        self.java_args = config.get("java_args", "-Xmx2G")
        
        # Check if Java args contains memory allocation, if not, recommend it
        if "-Xmx" not in self.java_args:
            memory_info = get_memory_info()
            recommended_memory = calculate_recommended_memory(memory_info)
            self.java_args = f"{self.java_args} {recommended_memory}"
            
        # Check Java installation
        self._check_java()
        
    def _check_java(self):
        """Check if Java is installed and configured properly."""
        java_installed = is_java_installed()
        if not java_installed:
            logging.warning("Java not found. Minecraft may not launch correctly.")
            return False
        return True
        
    def get_versions(self) -> List[str]:
        """Get installed Minecraft versions.
        
        Returns:
            List[str]: List of installed Minecraft versions.
        """
        versions = []
        versions_dir = os.path.join(self.minecraft_dir, "versions")
        
        if os.path.exists(versions_dir):
            for version_dir in os.listdir(versions_dir):
                json_path = os.path.join(versions_dir, version_dir, f"{version_dir}.json")
                if os.path.exists(json_path):
                    versions.append(version_dir)
        
        if not versions:
            # If no versions found, add some common ones for testing
            versions = ["1.20.2", "1.19.4", "1.18.2", "1.16.5"]
            
        return sorted(versions, reverse=True)
        
    def get_libraries(self, version: str) -> List[str]:
        """Get library paths for Minecraft version.
        
        Args:
            version (str): Minecraft version.
            
        Returns:
            List[str]: List of library paths.
        """
        libraries = []
        json_path = os.path.join(self.minecraft_dir, "versions", version, f"{version}.json")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    version_data = json.load(f)
                    
                libraries_data = version_data.get("libraries", [])
                for library in libraries_data:
                    # In a real implementation, this would parse the library info
                    # and resolve the correct JAR file path
                    pass
            except Exception as e:
                logging.error(f"Failed to parse version JSON: {e}")
        
        return libraries
        
    def launch(self, version: str, modpack_dir: Optional[str] = None, 
               callback: Optional[Callable[[str], None]] = None) -> subprocess.Popen:
        """Launch Minecraft.
        
        Args:
            version (str): Minecraft version.
            modpack_dir (Optional[str]): Path to modpack directory.
            callback (Optional[Callable[[str], None]]): Callback for log output.
            
        Returns:
            subprocess.Popen: Process object for the launched game.
        """
        # Verify Java installation
        if not self._check_java():
            raise RuntimeError("Java is not installed or not properly configured")
            
        # Build command
        cmd = [
            self.java_path
        ]
        
        # Add Java arguments
        for arg in self.java_args.split():
            cmd.append(arg)
            
        # Add game directory
        game_dir = self.minecraft_dir
        if modpack_dir:
            game_dir = modpack_dir
            
        cmd.extend([
            "-Djava.library.path=natives",
            f"-Dminecraft.client.jar={os.path.join(self.minecraft_dir, 'versions', version, f'{version}.jar')}",
            "-cp", self._build_classpath(version, modpack_dir),
            "net.minecraft.client.main.Main",
            "--username", "Player",
            "--version", version,
            "--gameDir", game_dir,
            "--assetsDir", os.path.join(self.minecraft_dir, "assets"),
            "--assetIndex", self._get_asset_index(version),
            "--uuid", "00000000-0000-0000-0000-000000000000",
            "--accessToken", "0",
            "--userType", "mojang"
        ])
        
        # Log command
        logging.info(f"Launching Minecraft with command: {' '.join(cmd)}")
        
        # Create process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        
        # Create thread to read and process output
        if callback:
            def read_output():
                for line in iter(process.stdout.readline, ""):
                    callback(line)
                process.stdout.close()
                
            def read_error():
                for line in iter(process.stderr.readline, ""):
                    callback(f"ERROR: {line}")
                process.stderr.close()
                
            threading.Thread(target=read_output, daemon=True).start()
            threading.Thread(target=read_error, daemon=True).start()
            
        return process
        
    def _build_classpath(self, version: str, modpack_dir: Optional[str] = None) -> str:
        """Build classpath for Minecraft launch.
        
        Args:
            version (str): Minecraft version.
            modpack_dir (Optional[str]): Path to modpack directory.
            
        Returns:
            str: Classpath string.
        """
        # In a real implementation, this would build the correct classpath
        # including all required libraries and mods
        # For now, just return a placeholder
        separator = ";" if platform.system() == "Windows" else ":"
        return f"{os.path.join(self.minecraft_dir, 'versions', version, f'{version}.jar')}"
        
    def _get_asset_index(self, version: str) -> str:
        """Get asset index for Minecraft version.
        
        Args:
            version (str): Minecraft version.
            
        Returns:
            str: Asset index.
        """
        # In a real implementation, this would parse the version JSON
        # and extract the correct asset index
        # For now, just derive it from the version
        if version.startswith("1.20"):
            return "4"
        elif version.startswith("1.19"):
            return "3"
        elif version.startswith("1.18"):
            return "2"
        elif version.startswith("1.17"):
            return "1"
        else:
            return "1.16"
            
    def check_compatibility(self, version: str, forge_version: Optional[str] = None) -> bool:
        """Check if Minecraft version is compatible with Forge version.
        
        Args:
            version (str): Minecraft version.
            forge_version (Optional[str]): Forge version.
            
        Returns:
            bool: True if compatible, False otherwise.
        """
        # In a real implementation, this would check compatibility between
        # Minecraft and Forge versions
        # For now, just return True
        return True