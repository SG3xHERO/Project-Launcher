#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Repository management for the Minecraft Modpack Launcher.
Modified to work with the custom modpack server.
"""

import os
import json
import logging
import requests
import tempfile
import platform
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from app.core.modpack import Modpack
from app.core.mods import Mod


@dataclass
class Repository:
    """Repository data model."""
    
    name: str
    url: str
    enabled: bool = True
    auth_token: Optional[str] = None
    last_updated: int = 0  # Unix timestamp
    modpacks: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def needs_update(self) -> bool:
        """Check if repository needs update.
        
        Returns:
            bool: True if repository needs update, False otherwise.
        """
        # Update if last update was more than 1 hour ago
        return time.time() - self.last_updated > 3600


class RepositoryManager:
    """Manager for repository operations."""
    
    def __init__(self, config):
        """Initialize repository manager.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.repositories = self._load_repositories()
        self.cache_dir = os.path.join("data", "cache", "repositories")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _load_repositories(self) -> Dict[str, Repository]:
        """Load repositories from configuration.
        
        Returns:
            Dict[str, Repository]: Dictionary mapping repository names to Repository instances.
        """
        repositories = {}
        
        # Get repositories from configuration
        repo_data = self.config.get("repositories", {})
        
        # Add default repository if none configured
        if not repo_data:
            # Use localhost for development, would be a real server URL in production
            server_url = self.config.get("server_url", "http://localhost:5000")
            
            repo_data = {
                "default": {
                    "name": "Default Repository",
                    "url": server_url,
                    "enabled": True
                }
            }
            self.config.set("repositories", repo_data)
            self.config.set("server_url", server_url)
            self.config.save()
            
        # Create Repository instances
        for repo_id, repo_info in repo_data.items():
            repositories[repo_id] = Repository(
                name=repo_info.get("name", repo_id),
                url=repo_info.get("url", ""),
                enabled=repo_info.get("enabled", True),
                auth_token=repo_info.get("auth_token"),
                last_updated=repo_info.get("last_updated", 0),
                modpacks=repo_info.get("modpacks", [])
            )
            
        return repositories
        
    def _save_repositories(self):
        """Save repositories to configuration."""
        repo_data = {}
        
        for repo_id, repo in self.repositories.items():
            repo_data[repo_id] = {
                "name": repo.name,
                "url": repo.url,
                "enabled": repo.enabled,
                "auth_token": repo.auth_token,
                "last_updated": repo.last_updated,
                "modpacks": repo.modpacks
            }
            
        self.config.set("repositories", repo_data)
        self.config.save()
        
    def add_repository(self, name: str, url: str) -> bool:
        """Add a repository.
        
        Args:
            name (str): Repository name.
            url (str): Repository URL.
            
        Returns:
            bool: True if repository was added successfully, False otherwise.
        """
        # Generate a safe ID from name
        repo_id = name.lower().replace(" ", "_").replace("-", "_")
        
        if repo_id in self.repositories:
            logging.warning(f"Repository with ID {repo_id} already exists")
            return False
            
        # Create repository
        self.repositories[repo_id] = Repository(
            name=name,
            url=url,
            enabled=True,
            last_updated=0
        )
        
        # Try to update the repository immediately
        success = self.update_repository(repo_id)
        
        # Save repositories
        self._save_repositories()
        
        return success
        
    def remove_repository(self, repo_id: str) -> bool:
        """Remove a repository.
        
        Args:
            repo_id (str): Repository ID.
            
        Returns:
            bool: True if repository was removed successfully, False otherwise.
        """
        if repo_id in self.repositories:
            del self.repositories[repo_id]
            self._save_repositories()
            return True
        else:
            logging.warning(f"Repository with ID {repo_id} not found")
            return False
            
    def get_repository(self, repo_id: str) -> Optional[Repository]:
        """Get repository by ID.
        
        Args:
            repo_id (str): Repository ID.
            
        Returns:
            Optional[Repository]: Repository instance or None if not found.
        """
        return self.repositories.get(repo_id)
        
    def get_enabled_repositories(self) -> List[Repository]:
        """Get enabled repositories.
        
        Returns:
            List[Repository]: List of enabled repositories.
        """
        return [repo for repo in self.repositories.values() if repo.enabled]
        
    def update_repository(self, repo_id: str) -> bool:
        """Update repository modpack list.
        
        Args:
            repo_id (str): Repository ID.
            
        Returns:
            bool: True if repository was updated successfully, False otherwise.
        """
        repo = self.repositories.get(repo_id)
        
        if not repo:
            logging.warning(f"Repository with ID {repo_id} not found")
            return False
            
        if not repo.enabled:
            logging.info(f"Repository {repo.name} is disabled, skipping update")
            return False
            
        try:
            # Build API URL
            api_url = f"{repo.url}/api/modpacks"
            
            # Set up headers
            headers = {}
            if repo.auth_token:
                headers["Authorization"] = f"Bearer {repo.auth_token}"
                
            # Make API request
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            if not isinstance(data, list):
                logging.error(f"Invalid response from repository {repo.name}: expected list")
                return False
                
            # Update repository data
            repo.modpacks = data
            repo.last_updated = int(time.time())
            
            # Save to cache
            cache_path = os.path.join(self.cache_dir, f"{repo_id}.json")
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=4)
                
            # Save repositories
            self._save_repositories()
            
            logging.info(f"Repository {repo.name} updated successfully with {len(data)} modpacks")
            return True
            
        except Exception as e:
            logging.error(f"Failed to update repository {repo.name}: {e}")
            
            # Try to load from cache if available
            cache_path = os.path.join(self.cache_dir, f"{repo_id}.json")
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r") as f:
                        repo.modpacks = json.load(f)
                    logging.info(f"Loaded repository {repo.name} from cache")
                    return True
                except Exception as cache_error:
                    logging.error(f"Failed to load repository {repo.name} from cache: {cache_error}")
                    
            return False
            
    def update_all_repositories(self) -> Dict[str, bool]:
        """Update all enabled repositories.
        
        Returns:
            Dict[str, bool]: Dictionary mapping repository IDs to update success status.
        """
        results = {}
        
        for repo_id, repo in self.repositories.items():
            if repo.enabled and repo.needs_update:
                results[repo_id] = self.update_repository(repo_id)
                
        return results
        
    def search_modpacks(self, query: str = "", mc_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for modpacks in repositories.
        
        Args:
            query (str): Search query.
            mc_version (Optional[str]): Minecraft version filter.
            
        Returns:
            List[Dict[str, Any]]: List of matching modpacks.
        """
        results = []
        
        # Normalize query
        query = query.lower().strip()
        
        # Search in all enabled repositories
        for repo in self.get_enabled_repositories():
            for modpack in repo.modpacks:
                # Check if modpack matches the query
                name = modpack.get("name", "").lower()
                description = modpack.get("description", "").lower()
                author = modpack.get("author", "").lower()
                
                if query and not (query in name or query in description or query in author):
                    continue
                    
                # Check if modpack supports the requested Minecraft version
                if mc_version and mc_version not in modpack.get("mc_versions", []):
                    continue
                    
                # Add repository information to the modpack data
                modpack_data = modpack.copy()
                modpack_data["repository"] = {
                    "id": repo.name.lower().replace(" ", "_").replace("-", "_"),
                    "name": repo.name,
                    "url": repo.url
                }
                
                results.append(modpack_data)
                
        return results
        
    def get_modpack_details(self, repo_id: str, modpack_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a modpack.
        
        Args:
            repo_id (str): Repository ID.
            modpack_id (str): Modpack ID.
            
        Returns:
            Optional[Dict[str, Any]]: Modpack details or None if not found.
        """
        repo = self.repositories.get(repo_id)
        
        if not repo or not repo.enabled:
            logging.warning(f"Repository with ID {repo_id} not found or disabled")
            return None
            
        # First, look for modpack in the cached list
        for modpack in repo.modpacks:
            if modpack.get("id") == modpack_id:
                return modpack
                
        # If not found, try to fetch directly from the API
        try:
            # Build API URL
            api_url = f"{repo.url}/api/modpacks/{modpack_id}"
            
            # Set up headers
            headers = {}
            if repo.auth_token:
                headers["Authorization"] = f"Bearer {repo.auth_token}"
                
            # Make API request
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Validate response
            if not isinstance(data, dict) or "id" not in data:
                logging.error(f"Invalid response from repository {repo.name}: expected modpack data")
                return None
                
            return data
            
        except Exception as e:
            logging.error(f"Failed to get modpack details from repository {repo.name}: {e}")
            return None
            
    def download_modpack(self, repo_id: str, modpack_id: str, target_path: str, 
                        progress_callback=None) -> bool:
        """Download modpack from repository.
        
        Args:
            repo_id (str): Repository ID.
            modpack_id (str): Modpack ID.
            target_path (str): Path to save downloaded modpack.
            progress_callback: Callback function for progress reporting.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        repo = self.repositories.get(repo_id)
        
        if not repo or not repo.enabled:
            logging.warning(f"Repository with ID {repo_id} not found or disabled")
            return False
            
        # Get modpack details
        modpack_details = self.get_modpack_details(repo_id, modpack_id)
        
        if not modpack_details:
            logging.error(f"Modpack with ID {modpack_id} not found in repository {repo.name}")
            return False
            
        # Get download URL
        download_url = modpack_details.get("download_url")
        
        if not download_url:
            logging.error(f"No download URL found for modpack {modpack_details.get('name', modpack_id)}")
            return False
            
        # If download URL is relative, make it absolute
        if not download_url.startswith("http"):
            download_url = f"{repo.url}{download_url}"
            
        try:
            # Set up headers
            headers = {}
            if repo.auth_token:
                headers["Authorization"] = f"Bearer {repo.auth_token}"
                
            # Download file with progress reporting
            response = requests.get(download_url, headers=headers, stream=True)
            response.raise_for_status()
            
            # Get content length if available
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Download file
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = downloaded_size / total_size
                            progress_callback(progress)
                            
            if progress_callback:
                progress_callback(1.0)  # 100% complete
                
            # Verify hash if provided
            file_hash = modpack_details.get("file_hash")
            if file_hash:
                from app.utils import calculate_checksum
                actual_hash = calculate_checksum(target_path, "sha256")
                
                if actual_hash != file_hash:
                    logging.warning(f"Hash mismatch for {modpack_id}")
                    logging.warning(f"Expected: {file_hash}")
                    logging.warning(f"Got: {actual_hash}")
                    # Continue anyway, as the server might have updated the modpack
                
            logging.info(f"Modpack {modpack_details.get('name', modpack_id)} downloaded successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to download modpack {modpack_details.get('name', modpack_id)}: {e}")
            
            # Clean up partial download
            if os.path.exists(target_path):
                os.remove(target_path)
                
            return False
    
    def get_modpack_icon(self, repo_id: str, modpack_id: str, target_path: str) -> bool:
        """Download modpack icon.
        
        Args:
            repo_id (str): Repository ID.
            modpack_id (str): Modpack ID.
            target_path (str): Path to save downloaded icon.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        repo = self.repositories.get(repo_id)
        
        if not repo or not repo.enabled:
            logging.warning(f"Repository with ID {repo_id} not found or disabled")
            return False
            
        # Build icon URL
        icon_url = f"{repo.url}/api/modpacks/{modpack_id}/icon"
        
        try:
            # Download icon
            response = requests.get(icon_url, timeout=10)
            
            # If icon doesn't exist, return False
            if response.status_code == 404:
                return False
                
            response.raise_for_status()
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Save icon
            with open(target_path, 'wb') as f:
                f.write(response.content)
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to download icon for modpack {modpack_id}: {e}")
            return False