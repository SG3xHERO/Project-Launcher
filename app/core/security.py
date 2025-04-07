#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Security utilities for the Minecraft Modpack Launcher.
"""

import os
import hashlib
import logging
import json
import requests
import tempfile
import zipfile
from typing import Dict, Any, Optional, List, Tuple


class SecurityManager:
    """Manager for security-related operations."""
    
    def __init__(self, config):
        """Initialize security manager.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.trusted_sources = self._load_trusted_sources()
        
    def _load_trusted_sources(self) -> Dict[str, Any]:
        """Load trusted sources from configuration.
        
        Returns:
            Dict[str, Any]: Trusted sources dictionary.
        """
        trusted_sources = self.config.get("trusted_sources", {})
        
        # Add default trusted sources if not present
        if not trusted_sources:
            trusted_sources = {
                "curseforge": {
                    "url": "https://www.curseforge.com",
                    "api_endpoint": "https://api.curseforge.com",
                    "trusted": True
                },
                "modrinth": {
                    "url": "https://modrinth.com",
                    "api_endpoint": "https://api.modrinth.com/v2",
                    "trusted": True
                }
            }
            self.config.set("trusted_sources", trusted_sources)
            self.config.save()
            
        return trusted_sources
        
    def verify_file_hash(self, file_path: str, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Verify file hash.
        
        Args:
            file_path (str): Path to file.
            expected_hash (str): Expected hash.
            algorithm (str): Hash algorithm.
            
        Returns:
            bool: True if hash matches, False otherwise.
        """
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return False
            
        if not expected_hash:
            logging.warning(f"No hash provided for {file_path}, skipping verification")
            return True
            
        hash_obj = None
        
        if algorithm.lower() == "sha256":
            hash_obj = hashlib.sha256()
        elif algorithm.lower() == "sha1":
            hash_obj = hashlib.sha1()
        elif algorithm.lower() == "md5":
            hash_obj = hashlib.md5()
        else:
            logging.error(f"Unsupported hash algorithm: {algorithm}")
            return False
            
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    hash_obj.update(byte_block)
                    
            calculated_hash = hash_obj.hexdigest()
            
            if calculated_hash.lower() == expected_hash.lower():
                logging.info(f"Hash verification successful for {file_path}")
                return True
            else:
                logging.warning(f"Hash verification failed for {file_path}")
                logging.warning(f"Expected: {expected_hash}")
                logging.warning(f"Calculated: {calculated_hash}")
                return False
                
        except Exception as e:
            logging.error(f"Error verifying hash for {file_path}: {e}")
            return False
            
    def scan_zip_for_malware(self, zip_path: str) -> Tuple[bool, Optional[str]]:
        """Scan ZIP file for potential malware or suspicious content.
        
        Args:
            zip_path (str): Path to ZIP file.
            
        Returns:
            Tuple[bool, Optional[str]]: (is_safe, reason_if_unsafe)
        """
        if not os.path.exists(zip_path):
            return False, "File not found"
            
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Check for suspicious file extensions
                suspicious_extensions = ['.exe', '.dll', '.jar', '.bat', '.sh', '.js', '.vbs', '.ps1']
                
                for file_info in zip_ref.infolist():
                    file_name = file_info.filename.lower()
                    
                    # Skip directories
                    if file_name.endswith('/'):
                        continue
                        
                    # Check for executables in unexpected locations
                    if any(file_name.endswith(ext) for ext in suspicious_extensions):
                        # Allow executables in known safe locations
                        if file_name.startswith('mods/') and file_name.endswith('.jar'):
                            # JAR files in mods directory are expected
                            continue
                            
                        return False, f"Suspicious file found: {file_info.filename}"
                        
                    # Check for very large files (potential zip bombs)
                    if file_info.file_size > 100 * 1024 * 1024:  # 100 MB
                        # Minecraft mods are typically under 100 MB
                        return False, f"Very large file found: {file_info.filename} ({file_info.file_size / 1024 / 1024:.2f} MB)"
                        
                    # Check compression ratio (potential zip bombs)
                    if file_info.compress_size > 0:
                        ratio = file_info.file_size / file_info.compress_size
                        if ratio > 100:  # Arbitrary threshold
                            return False, f"Suspicious compression ratio for {file_info.filename}: {ratio:.2f}"
                            
                # Scan for known malicious patterns in certain files
                for file_info in zip_ref.infolist():
                    file_name = file_info.filename.lower()
                    
                    # Skip directories and non-text files
                    if file_name.endswith('/') or not any(file_name.endswith(ext) for ext in ['.json', '.txt', '.cfg', '.properties', '.xml']):
                        continue
                        
                    # Extract and scan file
                    with tempfile.TemporaryDirectory() as temp_dir:
                        try:
                            zip_ref.extract(file_info, temp_dir)
                            file_path = os.path.join(temp_dir, file_info.filename)
                            
                            # Check if the file is actually text
                            with open(file_path, 'rb') as f:
                                # Read first 1024 bytes
                                header = f.read(1024)
                                
                                # Check if file contains binary data
                                if b'\0' in header:
                                    # Likely binary file with text extension
                                    return False, f"Binary data in text file: {file_info.filename}"
                                    
                            # For JSON files, check for potential command injection
                            if file_name.endswith('.json'):
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    try:
                                        content = f.read()
                                        
                                        # Check for suspicious patterns in JSON files
                                        suspicious_patterns = [
                                            '"java.exe', 'javaw.exe', 
                                            'Runtime.getRuntime', 'ProcessBuilder',
                                            'cmd.exe', 'powershell.exe', 'bash', 'sh -c',
                                            'curl ', 'wget ', 'http://', 'https://'
                                        ]
                                        
                                        for pattern in suspicious_patterns:
                                            if pattern in content:
                                                return False, f"Suspicious pattern '{pattern}' found in {file_info.filename}"
                                                
                                    except Exception:
                                        # Failed to parse, could be malformed on purpose
                                        return False, f"Malformed JSON file: {file_info.filename}"
                                        
                        except Exception as e:
                            logging.error(f"Error scanning {file_info.filename}: {e}")
                            
                return True, None
                
        except Exception as e:
            return False, f"Error scanning ZIP file: {e}"
            
    def is_url_trusted(self, url: str) -> bool:
        """Check if URL is from a trusted source.
        
        Args:
            url (str): URL to check.
            
        Returns:
            bool: True if URL is trusted, False otherwise.
        """
        for source_name, source_info in self.trusted_sources.items():
            if source_info.get("trusted", False) and url.startswith(source_info.get("url", "")):
                return True
                
        return False
        
    def add_trusted_source(self, name: str, url: str, api_endpoint: Optional[str] = None) -> bool:
        """Add a trusted source.
        
        Args:
            name (str): Source name.
            url (str): Source URL.
            api_endpoint (Optional[str]): API endpoint.
            
        Returns:
            bool: True if source was added successfully.
        """
        try:
            self.trusted_sources[name] = {
                "url": url,
                "api_endpoint": api_endpoint or url,
                "trusted": True
            }
            
            self.config.set("trusted_sources", self.trusted_sources)
            self.config.save()
            
            logging.info(f"Added trusted source: {name} ({url})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to add trusted source {name}: {e}")
            return False
            
    def remove_trusted_source(self, name: str) -> bool:
        """Remove a trusted source.
        
        Args:
            name (str): Source name.
            
        Returns:
            bool: True if source was removed successfully.
        """
        if name in self.trusted_sources:
            try:
                del self.trusted_sources[name]
                
                self.config.set("trusted_sources", self.trusted_sources)
                self.config.save()
                
                logging.info(f"Removed trusted source: {name}")
                return True
                
            except Exception as e:
                logging.error(f"Failed to remove trusted source {name}: {e}")
                
        return False