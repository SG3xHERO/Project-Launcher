#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minecraft version management and download for the Minecraft Modpack Launcher.
"""

import os
import json
import logging
import hashlib
import requests
import tempfile
import platform
import time
from typing import Dict, Any, Optional, List, Tuple

# Minecraft version manifest URL
VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"


class MinecraftDownloader:
    """Minecraft version downloader and manager."""
    
    def __init__(self, config):
        """Initialize Minecraft downloader.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.minecraft_dir = config.get("minecraft_directory")
        self.versions_dir = os.path.join(self.minecraft_dir, "versions")
        self.libraries_dir = os.path.join(self.minecraft_dir, "libraries")
        self.assets_dir = os.path.join(self.minecraft_dir, "assets")
        self.ensure_directories()
        
    def ensure_directories(self):
        """Ensure required directories exist."""
        os.makedirs(self.minecraft_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)
        os.makedirs(self.libraries_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "indexes"), exist_ok=True)
        os.makedirs(os.path.join(self.assets_dir, "objects"), exist_ok=True)
        
    def get_version_manifest(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get Minecraft version manifest.
        
        Args:
            force_refresh (bool): Force refresh from remote.
            
        Returns:
            Optional[Dict[str, Any]]: Version manifest or None if failed.
        """
        manifest_path = os.path.join(self.minecraft_dir, "version_manifest.json")
        
        # Check if manifest exists and is recent (less than 24 hours old)
        if not force_refresh and os.path.exists(manifest_path):
            manifest_age = time.time() - os.path.getmtime(manifest_path)
            if manifest_age < 86400:  # 24 hours
                try:
                    with open(manifest_path, "r") as f:
                        return json.load(f)
                except Exception as e:
                    logging.error(f"Failed to read version manifest: {e}")
        
        # Download manifest
        try:
            response = requests.get(VERSION_MANIFEST_URL, timeout=10)
            response.raise_for_status()
            
            manifest = response.json()
            
            # Save manifest
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
                
            return manifest
            
        except Exception as e:
            logging.error(f"Failed to download version manifest: {e}")
            
            # Try to read existing manifest
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r") as f:
                        return json.load(f)
                except Exception as ex:
                    logging.error(f"Failed to read existing version manifest: {ex}")
                    
            return None
            
    def get_available_versions(self) -> List[Dict[str, Any]]:
        """Get list of available Minecraft versions.
        
        Returns:
            List[Dict[str, Any]]: List of available versions.
        """
        manifest = self.get_version_manifest()
        if not manifest:
            return []
            
        return manifest.get("versions", [])
        
    def get_installed_versions(self) -> List[str]:
        """Get list of installed Minecraft versions.
        
        Returns:
            List[str]: List of installed version IDs.
        """
        versions = []
        
        if os.path.exists(self.versions_dir):
            for version_dir in os.listdir(self.versions_dir):
                json_path = os.path.join(self.versions_dir, version_dir, f"{version_dir}.json")
                jar_path = os.path.join(self.versions_dir, version_dir, f"{version_dir}.jar")
                
                if os.path.exists(json_path) and os.path.exists(jar_path):
                    versions.append(version_dir)
                    
        return sorted(versions, reverse=True)
        
    def is_version_installed(self, version_id: str) -> bool:
        """Check if a Minecraft version is installed.
        
        Args:
            version_id (str): Version ID to check.
            
        Returns:
            bool: True if version is installed, False otherwise.
        """
        json_path = os.path.join(self.versions_dir, version_id, f"{version_id}.json")
        jar_path = os.path.join(self.versions_dir, version_id, f"{version_id}.jar")
        
        return os.path.exists(json_path) and os.path.exists(jar_path)
        
    def get_version_info(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Minecraft version.
        
        Args:
            version_id (str): Version ID.
            
        Returns:
            Optional[Dict[str, Any]]: Version information or None if not found.
        """
        # First check if we have this version locally
        json_path = os.path.join(self.versions_dir, version_id, f"{version_id}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to read version info: {e}")
                
        # If not, try to find it in the manifest
        manifest = self.get_version_manifest()
        if manifest:
            for version in manifest.get("versions", []):
                if version.get("id") == version_id:
                    try:
                        # Download version info
                        url = version.get("url")
                        if url:
                            response = requests.get(url, timeout=10)
                            response.raise_for_status()
                            return response.json()
                    except Exception as e:
                        logging.error(f"Failed to download version info: {e}")
                        
        return None
        
    def download_version(self, version_id: str, progress_callback=None) -> bool:
        """Download a Minecraft version.
        
        Args:
            version_id (str): Version ID to download.
            progress_callback: Callback function for progress reporting.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        if self.is_version_installed(version_id):
            logging.info(f"Minecraft version {version_id} is already installed")
            if progress_callback:
                progress_callback(1.0, "Already installed")
            return True
            
        # Get version info
        version_info = self.get_version_info(version_id)
        if not version_info:
            logging.error(f"Failed to get info for version {version_id}")
            return False
            
        # Create version directory
        version_dir = os.path.join(self.versions_dir, version_id)
        os.makedirs(version_dir, exist_ok=True)
        
        # Save version info
        json_path = os.path.join(version_dir, f"{version_id}.json")
        with open(json_path, "w") as f:
            json.dump(version_info, f, indent=2)
            
        if progress_callback:
            progress_callback(0.1, "Downloading client JAR...")
            
        # Download client JAR
        client_url = version_info.get("downloads", {}).get("client", {}).get("url")
        client_sha1 = version_info.get("downloads", {}).get("client", {}).get("sha1")
        
        if not client_url:
            logging.error(f"No client URL found for version {version_id}")
            return False
            
        jar_path = os.path.join(version_dir, f"{version_id}.jar")
        if not self._download_file(client_url, jar_path, client_sha1):
            logging.error(f"Failed to download client JAR for version {version_id}")
            return False
            
        # Download assets index
        if progress_callback:
            progress_callback(0.2, "Downloading assets index...")
            
        assets_index = version_info.get("assetIndex", {})
        assets_index_url = assets_index.get("url")
        assets_index_id = assets_index.get("id")
        
        if assets_index_url and assets_index_id:
            # Download assets index
            assets_index_path = os.path.join(self.assets_dir, "indexes", f"{assets_index_id}.json")
            if not self._download_file(assets_index_url, assets_index_path):
                logging.error(f"Failed to download assets index for version {version_id}")
                return False
                
            # Download assets
            if progress_callback:
                progress_callback(0.3, "Downloading assets...")
                
            try:
                with open(assets_index_path, "r") as f:
                    assets_data = json.load(f)
                    
                objects = assets_data.get("objects", {})
                total_objects = len(objects)
                downloaded_objects = 0
                
                for asset_path, asset_info in objects.items():
                    # Get asset hash
                    asset_hash = asset_info.get("hash")
                    if not asset_hash:
                        continue
                        
                    # Determine asset path
                    hash_prefix = asset_hash[:2]
                    asset_object_path = os.path.join(self.assets_dir, "objects", hash_prefix, asset_hash)
                    
                    # Skip if already exists
                    if os.path.exists(asset_object_path):
                        downloaded_objects += 1
                        if progress_callback:
                            progress = 0.3 + (downloaded_objects / total_objects) * 0.3
                            progress_callback(progress, f"Downloading assets ({downloaded_objects}/{total_objects})...")
                        continue
                        
                    # Download asset
                    asset_url = f"https://resources.download.minecraft.net/{hash_prefix}/{asset_hash}"
                    os.makedirs(os.path.dirname(asset_object_path), exist_ok=True)
                    
                    if not self._download_file(asset_url, asset_object_path, asset_hash):
                        logging.warning(f"Failed to download asset {asset_path}")
                        
                    downloaded_objects += 1
                    if progress_callback:
                        progress = 0.3 + (downloaded_objects / total_objects) * 0.3
                        progress_callback(progress, f"Downloading assets ({downloaded_objects}/{total_objects})...")
                        
            except Exception as e:
                logging.error(f"Failed to process assets: {e}")
                # Continue with libraries anyway
        
        # Download libraries
        if progress_callback:
            progress_callback(0.6, "Downloading libraries...")
            
        libraries = version_info.get("libraries", [])
        total_libraries = len(libraries)
        downloaded_libraries = 0
        
        for library in libraries:
            # Check if library is for current OS
            if not self._should_download_library(library):
                downloaded_libraries += 1
                continue
                
            # Get download info
            downloads = library.get("downloads", {})
            artifact = downloads.get("artifact")
            
            if artifact:
                path = artifact.get("path")
                url = artifact.get("url")
                sha1 = artifact.get("sha1")
                
                if path and url:
                    library_path = os.path.join(self.libraries_dir, path)
                    os.makedirs(os.path.dirname(library_path), exist_ok=True)
                    
                    if not os.path.exists(library_path):
                        if not self._download_file(url, library_path, sha1):
                            logging.warning(f"Failed to download library {path}")
                            
            # Get OS-specific classifiers
            classifiers = downloads.get("classifiers", {})
            if classifiers:
                # Determine classifier based on OS
                classifier_key = None
                if platform.system() == "Windows":
                    if platform.architecture()[0] == "64bit":
                        classifier_key = "natives-windows-64"
                    else:
                        classifier_key = "natives-windows"
                elif platform.system() == "Linux":
                    classifier_key = "natives-linux"
                elif platform.system() == "Darwin":  # macOS
                    classifier_key = "natives-macos"
                    
                if classifier_key and classifier_key in classifiers:
                    classifier = classifiers[classifier_key]
                    url = classifier.get("url")
                    path = classifier.get("path")
                    sha1 = classifier.get("sha1")
                    
                    if path and url:
                        native_path = os.path.join(self.libraries_dir, path)
                        os.makedirs(os.path.dirname(native_path), exist_ok=True)
                        
                        if not os.path.exists(native_path):
                            if not self._download_file(url, native_path, sha1):
                                logging.warning(f"Failed to download native library {path}")
                                
            downloaded_libraries += 1
            if progress_callback:
                progress = 0.6 + (downloaded_libraries / total_libraries) * 0.4
                progress_callback(progress, f"Downloading libraries ({downloaded_libraries}/{total_libraries})...")
                
        if progress_callback:
            progress_callback(1.0, "Download complete")
            
        return True
        
    def _should_download_library(self, library: Dict[str, Any]) -> bool:
        """Check if a library should be downloaded for the current system.
        
        Args:
            library (Dict[str, Any]): Library information.
            
        Returns:
            bool: True if library should be downloaded, False otherwise.
        """
        # Check rules
        rules = library.get("rules", [])
        if not rules:
            return True
            
        # Process rules
        allowed = None
        
        for rule in rules:
            action = rule.get("action", "allow")
            os_info = rule.get("os", {})
            
            if os_info:
                os_name = os_info.get("name")
                
                if os_name:
                    # Convert platform.system() to Minecraft's OS names
                    current_os = None
                    if platform.system() == "Windows":
                        current_os = "windows"
                    elif platform.system() == "Linux":
                        current_os = "linux"
                    elif platform.system() == "Darwin":
                        current_os = "osx"
                        
                    # Apply rule if OS matches
                    if os_name == current_os:
                        allowed = (action == "allow")
                    # Skip rule if OS doesn't match
                    else:
                        continue
                        
            else:
                # Rule applies to all OSes
                allowed = (action == "allow")
                
        # If no rules matched, default to allowed
        return allowed if allowed is not None else True
        
    def _download_file(self, url: str, path: str, expected_hash: Optional[str] = None, 
                      hash_algorithm: str = "sha1") -> bool:
        """Download a file with optional hash verification.
        
        Args:
            url (str): URL to download.
            path (str): Path to save the file.
            expected_hash (Optional[str]): Expected hash value.
            hash_algorithm (str): Hash algorithm to use.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        # Skip if file already exists and hash matches
        if os.path.exists(path) and expected_hash:
            file_hash = self._calculate_hash(path, hash_algorithm)
            if file_hash and file_hash.lower() == expected_hash.lower():
                return True
                
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        try:
            # Download file
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            # Verify hash if provided
            if expected_hash:
                file_hash = self._calculate_hash(path, hash_algorithm)
                if not file_hash or file_hash.lower() != expected_hash.lower():
                    logging.warning(f"Hash mismatch for {path}")
                    logging.warning(f"Expected: {expected_hash}")
                    logging.warning(f"Got: {file_hash}")
                    os.remove(path)
                    return False
                    
            return True
            
        except Exception as e:
            logging.error(f"Failed to download {url}: {e}")
            
            # Clean up partial download
            if os.path.exists(path):
                os.remove(path)
                
            return False
            
    def _calculate_hash(self, file_path: str, algorithm: str = "sha1") -> Optional[str]:
        """Calculate file hash.
        
        Args:
            file_path (str): Path to file.
            algorithm (str): Hash algorithm.
            
        Returns:
            Optional[str]: Calculated hash or None if error.
        """
        try:
            hash_obj = None
            
            if algorithm.lower() == "sha1":
                hash_obj = hashlib.sha1()
            elif algorithm.lower() == "sha256":
                hash_obj = hashlib.sha256()
            elif algorithm.lower() == "md5":
                hash_obj = hashlib.md5()
            else:
                logging.error(f"Unsupported hash algorithm: {algorithm}")
                return None
                
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    hash_obj.update(byte_block)
                    
            return hash_obj.hexdigest()
            
        except Exception as e:
            logging.error(f"Failed to calculate hash for {file_path}: {e}")
            return None