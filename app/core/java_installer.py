#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Java installation manager for the Minecraft Modpack Launcher.
"""

import os
import sys
import subprocess
import platform
import logging
import requests
import tempfile
import json
import shutil
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

ADOPTIUM_API = "https://api.adoptium.net/v3/assets/latest/21/hotspot"


class JavaInstaller:
    """Java installation manager for Minecraft."""
    
    def __init__(self, config):
        """Initialize Java installer.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.java_dir = os.path.join("data", "java")
        os.makedirs(self.java_dir, exist_ok=True)
        
    def get_installed_java_versions(self) -> List[Dict[str, Any]]:
        """Get list of installed Java versions.
        
        Returns:
            List[Dict[str, Any]]: List of installed Java versions.
        """
        versions = []
        
        # Check for Java installations in the launcher directory
        if os.path.exists(self.java_dir):
            for java_folder in os.listdir(self.java_dir):
                java_path = os.path.join(self.java_dir, java_folder)
                
                if os.path.isdir(java_path):
                    # Determine the java executable path based on platform
                    if platform.system() == "Windows":
                        java_exe = os.path.join(java_path, "bin", "javaw.exe")
                    else:
                        java_exe = os.path.join(java_path, "bin", "java")
                        
                    if os.path.exists(java_exe):
                        # Check version
                        version_info = self._get_java_version(java_exe)
                        if version_info:
                            versions.append({
                                "path": java_exe,
                                "folder": java_path,
                                "version": version_info.get("version", "Unknown"),
                                "version_number": version_info.get("version_number", 0),
                                "vendor": version_info.get("vendor", "Unknown")
                            })
                            
        # Also check system Java installations
        system_java = self._find_system_java()
        if system_java:
            versions.append(system_java)
                
        return sorted(versions, key=lambda x: x.get("version_number", 0), reverse=True)
    
    def _get_java_version(self, java_path: str) -> Optional[Dict[str, Any]]:
        """Get Java version information.
        
        Args:
            java_path (str): Path to Java executable.
            
        Returns:
            Optional[Dict[str, Any]]: Java version information or None if failed.
        """
        try:
            # Run java -version and capture output
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Java outputs version to stderr
            output = result.stderr
            
            if "version" in output:
                # Parse version string
                import re
                
                # Extract version
                version_match = re.search(r'version "([^"]+)"', output)
                if version_match:
                    version = version_match.group(1)
                    
                    # Extract numeric version (for sorting)
                    version_number_match = re.search(r'(\d+)\.(\d+)\.', version)
                    if version_number_match:
                        major = int(version_number_match.group(1))
                        minor = int(version_number_match.group(2))
                        version_number = major * 100 + minor
                    else:
                        # Handle version formats like "21" (Java 21)
                        simple_version_match = re.search(r'(\d+)', version)
                        if simple_version_match:
                            major = int(simple_version_match.group(1))
                            version_number = major * 100
                        else:
                            version_number = 0
                            
                    # Extract vendor
                    vendor_match = re.search(r'^(.+?)\s+version', output, re.MULTILINE)
                    vendor = vendor_match.group(1) if vendor_match else "Unknown"
                    
                    return {
                        "version": version,
                        "version_number": version_number,
                        "vendor": vendor
                    }
                    
            return None
            
        except Exception as e:
            logging.error(f"Failed to get Java version from {java_path}: {e}")
            return None
            
    def _find_system_java(self) -> Optional[Dict[str, Any]]:
        """Find system Java installation.
        
        Returns:
            Optional[Dict[str, Any]]: System Java information or None if not found.
        """
        java_cmd = "java"
        
        try:
            # Check if java is in PATH
            if platform.system() == "Windows":
                # Use where command
                result = subprocess.run(
                    ["where", java_cmd],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    java_path = result.stdout.strip().split('\n')[0]
                else:
                    return None
            else:
                # Use which command
                result = subprocess.run(
                    ["which", java_cmd],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    java_path = result.stdout.strip()
                else:
                    return None
                    
            # Get version information
            version_info = self._get_java_version(java_path)
            if version_info:
                return {
                    "path": java_path,
                    "folder": str(Path(java_path).parent.parent),
                    "version": version_info.get("version", "Unknown"),
                    "version_number": version_info.get("version_number", 0),
                    "vendor": version_info.get("vendor", "Unknown"),
                    "system": True
                }
                
            return None
            
        except Exception as e:
            logging.error(f"Failed to find system Java: {e}")
            return None
            
    def get_latest_java_url(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get download URL for latest Java 21.
        
        Returns:
            Tuple[Optional[str], Optional[str], Optional[str]]: 
                (download_url, file_name, checksum) or (None, None, None) if failed.
        """
        try:
            # Determine current OS and architecture
            os_name = platform.system().lower()
            if os_name == "darwin":
                os_name = "mac"
                
            arch = platform.machine().lower()
            if arch == "amd64" or arch == "x86_64":
                arch = "x64"
            elif arch == "aarch64" or arch == "arm64":
                arch = "aarch64"
                
            # Request available versions
            response = requests.get(
                f"{ADOPTIUM_API}?os={os_name}&architecture={arch}",
                timeout=10
            )
            response.raise_for_status()
            
            # Parse response
            assets = response.json()
            if not assets or not isinstance(assets, list) or len(assets) == 0:
                logging.error("No Java assets found")
                return None, None, None
                
            # Get first (latest) asset
            asset = assets[0]
            binary = asset.get("binary", {})
            
            # Get download URL and package type based on OS
            package = binary.get("package", {})
            download_url = package.get("link")
            checksum = package.get("checksum")
            file_name = os.path.basename(download_url) if download_url else None
            
            return download_url, file_name, checksum
            
        except Exception as e:
            logging.error(f"Failed to get Java download URL: {e}")
            return None, None, None
            
    def download_and_install_java(self, progress_callback=None) -> Optional[Dict[str, Any]]:
        """Download and install latest Java 21.
        
        Args:
            progress_callback: Callback function for progress reporting.
            
        Returns:
            Optional[Dict[str, Any]]: Installed Java information or None if failed.
        """
        try:
            # Get download URL
            download_url, file_name, checksum = self.get_latest_java_url()
            if not download_url or not file_name:
                logging.error("Failed to get Java download URL")
                return None
                
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download Java
                if progress_callback:
                    progress_callback(0.1, "Downloading Java...")
                    
                download_path = os.path.join(temp_dir, file_name)
                
                # Download file
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                
                # Get content length if available
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress = 0.1 + (downloaded_size / total_size) * 0.4
                                progress_callback(progress, "Downloading Java...")
                                
                if progress_callback:
                    progress_callback(0.5, "Extracting Java...")
                    
                # Extract Java
                extract_dir = os.path.join(temp_dir, "extract")
                os.makedirs(extract_dir, exist_ok=True)
                
                # Different extraction based on file type
                if file_name.endswith(".zip"):
                    import zipfile
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                elif file_name.endswith(".tar.gz"):
                    import tarfile
                    with tarfile.open(download_path, "r:gz") as tar_ref:
                        tar_ref.extractall(extract_dir)
                elif file_name.endswith(".msi") or file_name.endswith(".exe"):
                    # For Windows installers, use a different approach
                    if platform.system() == "Windows":
                        if file_name.endswith(".msi"):
                            # Use msiexec to extract files
                            subprocess.run(
                                ["msiexec", "/a", download_path, "/qn", f"TARGETDIR={extract_dir}"],
                                check=True
                            )
                        else:
                            # For EXE installers, inform the user
                            if progress_callback:
                                progress_callback(1.0, "Manual installation required")
                            return {
                                "path": download_path,
                                "needs_manual_install": True
                            }
                else:
                    logging.error(f"Unsupported file type: {file_name}")
                    return None
                    
                if progress_callback:
                    progress_callback(0.7, "Installing Java...")
                    
                # Find Java home in extracted directory
                java_home = self._find_java_home(extract_dir)
                if not java_home:
                    logging.error("Could not find Java home in extracted files")
                    return None
                    
                # Create target directory
                target_dir = os.path.join(self.java_dir, f"jdk-21-{platform.system().lower()}")
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                    
                # Copy Java to target directory
                shutil.copytree(java_home, target_dir)
                
                if progress_callback:
                    progress_callback(0.9, "Configuring Java...")
                    
                # Determine java executable path
                if platform.system() == "Windows":
                    java_exe = os.path.join(target_dir, "bin", "javaw.exe")
                else:
                    java_exe = os.path.join(target_dir, "bin", "java")
                    # Make executable on Unix
                    if os.path.exists(java_exe):
                        os.chmod(java_exe, 0o755)
                        
                # Verify installation
                version_info = self._get_java_version(java_exe)
                if not version_info:
                    logging.error("Failed to verify Java installation")
                    return None
                    
                # Update configuration
                self.config.set("java_path", java_exe)
                self.config.save()
                
                if progress_callback:
                    progress_callback(1.0, "Java installation complete")
                    
                return {
                    "path": java_exe,
                    "folder": target_dir,
                    "version": version_info.get("version", "Unknown"),
                    "version_number": version_info.get("version_number", 0),
                    "vendor": version_info.get("vendor", "Unknown")
                }
                
        except Exception as e:
            logging.error(f"Failed to install Java: {e}")
            if progress_callback:
                progress_callback(1.0, f"Error: {str(e)}")
            return None
            
    def _find_java_home(self, directory: str) -> Optional[str]:
        """Find Java home directory in extracted files.
        
        Args:
            directory (str): Directory to search.
            
        Returns:
            Optional[str]: Java home directory or None if not found.
        """
        # First, check for bin/java executable
        for root, dirs, files in os.walk(directory):
            bin_dir = os.path.join(root, "bin")
            if os.path.isdir(bin_dir):
                java_exec = "java.exe" if platform.system() == "Windows" else "java"
                java_path = os.path.join(bin_dir, java_exec)
                
                if os.path.exists(java_path):
                    # Found Java executable, return parent directory
                    return root
                    
        # If not found, look for common JDK directory naming patterns
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and (
                item.startswith("jdk") or 
                item.startswith("temurin") or
                "jdk" in item.lower()
            ):
                # Check if this directory contains bin/java
                java_exec = "java.exe" if platform.system() == "Windows" else "java"
                java_path = os.path.join(item_path, "bin", java_exec)
                
                if os.path.exists(java_path):
                    return item_path
                    
        return None