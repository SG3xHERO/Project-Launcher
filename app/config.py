#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration management for the Minecraft Modpack Launcher.
"""

import os
import json
import logging
from pathlib import Path


class Config:
    """Configuration handler for the Minecraft Modpack Launcher."""

    def __init__(self, config_path=None):
        """Initialize configuration handler.
        
        Args:
            config_path (str, optional): Path to the configuration file.
                Defaults to ./data/config.json.
        """
        self.config_path = config_path or os.path.join("data", "config.json")
        self.config = {}
        
    def load(self):
        """Load configuration from file.
        
        Returns:
            bool: True if configuration was loaded successfully, False otherwise.
        """
        if not os.path.exists(self.config_path):
            logging.info(f"Configuration file not found at {self.config_path}")
            return False
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            logging.info(f"Configuration loaded from {self.config_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            return False
            
    def save(self):
        """Save configuration to file.
        
        Returns:
            bool: True if configuration was saved successfully, False otherwise.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            logging.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")
            return False
            
    def create_default(self):
        """Create default configuration."""
        self.config = {
            "minecraft_directory": self._get_default_minecraft_dir(),
            "minecraft_version": "1.19.4",
            "java_path": self._get_default_java_path(),
            "java_args": "-Xmx2G -XX:+UseG1GC -XX:+ParallelRefProcEnabled",
            "server_url": "http://localhost:5000",
            "repositories": {
                "default": {
                    "name": "Default Repository",
                    "url": "http://localhost:5000",
                    "enabled": True
                }
            },
            "check_for_updates": True,
            "max_download_threads": 3,
            "launcher_theme": "default",
            "first_run": True
        }
    
    def get(self, key, default=None):
        """Get configuration value by key.
        
        Args:
            key (str): Configuration key.
            default: Default value to return if key is not found.
            
        Returns:
            The configuration value or default.
        """
        return self.config.get(key, default)
        
    def set(self, key, value):
        """Set configuration value.
        
        Args:
            key (str): Configuration key.
            value: Configuration value.
        """
        self.config[key] = value
        
    def _get_default_minecraft_dir(self):
        """Get default Minecraft directory.
        
        Returns:
            str: Path to default Minecraft directory.
        """
        home = Path.home()
        
        if os.name == "nt":  # Windows
            return os.path.join(str(home), "AppData", "Roaming", ".minecraft")
        elif os.name == "posix":  # Linux, macOS, etc.
            if os.path.exists("/Applications"):  # macOS
                return os.path.join(str(home), "Library", "Application Support", "minecraft")
            else:  # Linux
                return os.path.join(str(home), ".minecraft")
        else:
            # Default fallback
            return os.path.join(str(home), ".minecraft")
            
    def _get_default_java_path(self):
        """Get default Java executable path.
        
        Returns:
            str: Path to Java executable.
        """
        # Try to find Java in common locations
        if os.name == "nt":  # Windows
            # First, try to run where java
            try:
                import subprocess
                result = subprocess.run(["where", "java"], capture_output=True, text=True, check=False)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.splitlines()[0].strip()
            except Exception:
                pass
                
            # Try common installation paths
            for program_files in ["Program Files", "Program Files (x86)"]:
                java_path = os.path.join("C:\\", program_files, "Java")
                if os.path.exists(java_path):
                    # Find newest Java version
                    java_versions = [d for d in os.listdir(java_path) if d.startswith("jre") or d.startswith("jdk")]
                    if java_versions:
                        newest_version = sorted(java_versions)[-1]
                        return os.path.join(java_path, newest_version, "bin", "java.exe")
            
            # If not found, return default command which will use PATH
            return "java.exe"
        else:  # Linux, macOS, etc.
            # Try to find Java using 'which'
            try:
                import subprocess
                result = subprocess.run(["which", "java"], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
                
            # If not found, return default command which will use PATH
            return "java"