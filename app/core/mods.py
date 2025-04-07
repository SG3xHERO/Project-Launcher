#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mod management for the Minecraft Modpack Launcher.
"""

import os
import json
import logging
import hashlib
import requests
import concurrent.futures
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set


@dataclass
class Mod:
    """Mod data model."""
    
    id: str
    name: str
    version: str
    mc_versions: List[str]
    download_url: str
    file_name: Optional[str] = None
    file_size: int = 0
    file_hash: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    def is_compatible_with(self, mc_version: str) -> bool:
        """Check if mod is compatible with Minecraft version.
        
        Args:
            mc_version (str): Minecraft version.
            
        Returns:
            bool: True if mod is compatible, False otherwise.
        """
        return mc_version in self.mc_versions
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert mod to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of mod.
        """
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mod':
        """Create mod from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of mod.
            
        Returns:
            Mod: Created mod.
        """
        return cls(**data)


class ModManager:
    """Manager for mod operations."""
    
    def __init__(self, config):
        """Initialize mod manager.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.mod_cache_path = os.path.join("data", "mod_cache.json")
        self.mod_cache = self._load_mod_cache()
    
    def _load_mod_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load mod cache from disk.
        
        Returns:
            Dict[str, Dict[str, Any]]: Mod cache.
        """
        if os.path.exists(self.mod_cache_path):
            try:
                with open(self.mod_cache_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load mod cache: {e}")
        
        return {}
    
    def _save_mod_cache(self):
        """Save mod cache to disk."""
        try:
            os.makedirs(os.path.dirname(self.mod_cache_path), exist_ok=True)
            with open(self.mod_cache_path, "w") as f:
                json.dump(self.mod_cache, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save mod cache: {e}")
    
    def download_mod(self, mod: Mod, target_dir: str) -> bool:
        """Download mod to target directory.
        
        Args:
            mod (Mod): Mod to download.
            target_dir (str): Target directory for downloaded mod.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        os.makedirs(target_dir, exist_ok=True)
        
        # If file_name is not provided, extract it from download URL
        if not mod.file_name:
            mod.file_name = os.path.basename(mod.download_url)
        
        target_path = os.path.join(target_dir, mod.file_name)
        
        # Check if mod is already downloaded
        if os.path.exists(target_path):
            # Verify file hash if available
            if mod.file_hash:
                file_hash = self._calculate_file_hash(target_path)
                if file_hash == mod.file_hash:
                    logging.info(f"Mod {mod.name} already downloaded")
                    return True
                else:
                    logging.warning(f"Mod {mod.name} hash mismatch, re-downloading")
            else:
                logging.info(f"Mod {mod.name} already exists, skipping download")
                return True
        
        try:
            logging.info(f"Downloading mod {mod.name} from {mod.download_url}")
            
            # Download file with progress reporting
            response = requests.get(mod.download_url, stream=True)
            response.raise_for_status()
            
            # Get content length if available
            total_size = int(response.headers.get('content-length', 0))
            mod.file_size = total_size
            
            # Download file
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Calculate file hash
            if not mod.file_hash:
                mod.file_hash = self._calculate_file_hash(target_path)
            
            # Update mod cache
            self.mod_cache[mod.id] = mod.to_dict()
            self._save_mod_cache()
            
            logging.info(f"Mod {mod.name} downloaded successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to download mod {mod.name}: {e}")
            
            # Clean up partial download
            if os.path.exists(target_path):
                os.remove(target_path)
                
            return False
    
    def download_mods_parallel(self, mods: List[Mod], target_dir: str) -> Dict[str, bool]:
        """Download multiple mods in parallel.
        
        Args:
            mods (List[Mod]): Mods to download.
            target_dir (str): Target directory for downloaded mods.
            
        Returns:
            Dict[str, bool]: Dictionary mapping mod IDs to download success status.
        """
        results = {}
        max_workers = self.config.get("max_download_threads", 3)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_mod = {
                executor.submit(self.download_mod, mod, target_dir): mod
                for mod in mods
            }
            
            for future in concurrent.futures.as_completed(future_to_mod):
                mod = future_to_mod[future]
                try:
                    success = future.result()
                    results[mod.id] = success
                except Exception as e:
                    logging.error(f"Download of mod {mod.name} raised exception: {e}")
                    results[mod.id] = False
                    
        return results
    
    def check_mod_dependencies(self, mod: Mod, installed_mods: Dict[str, Mod]) -> Set[str]:
        """Check mod dependencies.
        
        Args:
            mod (Mod): Mod to check dependencies for.
            installed_mods (Dict[str, Mod]): Dictionary of installed mods.
            
        Returns:
            Set[str]: Set of missing dependency mod IDs.
        """
        missing_dependencies = set()
        
        for dep_id in mod.dependencies:
            if dep_id not in installed_mods:
                missing_dependencies.add(dep_id)
                
        return missing_dependencies
    
    def resolve_dependencies(self, mods: List[Mod]) -> List[Mod]:
        """Resolve dependencies for a list of mods.
        
        Args:
            mods (List[Mod]): List of mods to resolve dependencies for.
            
        Returns:
            List[Mod]: List of mods with dependencies resolved.
        """
        # In a real implementation, this would fetch dependency information
        # from a mod repository or catalog and add required mods to the list
        # For now, just return the original list
        return mods
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file.
        
        Args:
            file_path (str): Path to file.
            
        Returns:
            str: SHA-256 hash of file.
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        return sha256_hash.hexdigest()
    
    def get_mod_by_id(self, mod_id: str) -> Optional[Mod]:
        """Get mod by ID from cache.
        
        Args:
            mod_id (str): Mod ID.
            
        Returns:
            Optional[Mod]: Mod instance or None if not found.
        """
        if mod_id in self.mod_cache:
            return Mod.from_dict(self.mod_cache[mod_id])
        return None
    
    def search_mods(self, query: str, mc_version: Optional[str] = None) -> List[Mod]:
        """Search for mods.
        
        Args:
            query (str): Search query.
            mc_version (Optional[str]): Minecraft version filter.
            
        Returns:
            List[Mod]: List of matching mods.
        """
        # In a real implementation, this would search a mod repository or catalog
        # For now, just return an empty list
        return []