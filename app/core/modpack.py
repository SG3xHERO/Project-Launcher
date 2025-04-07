#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modpack management for the Minecraft Modpack Launcher.
"""

import os
import json
import logging
import shutil
import zipfile
import tempfile
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

from app.core.mods import Mod, ModManager


@dataclass
class Modpack:
    """Modpack data model."""
    
    id: str
    name: str
    version: str
    mc_versions: List[str]
    author: str
    description: str
    icon_path: Optional[str] = None
    mods: List[Dict[str, Any]] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    resource_packs: List[Dict[str, Any]] = field(default_factory=list)
    install_path: Optional[str] = None
    
    @property
    def is_installed(self) -> bool:
        """Check if modpack is installed."""
        return self.install_path is not None and os.path.exists(self.install_path)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert modpack to dictionary."""
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Modpack':
        """Create modpack from dictionary."""
        return cls(**data)
        
    @classmethod
    def from_json(cls, json_path: str) -> 'Modpack':
        """Create modpack from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class ModpackManager:
    """Manager for modpack operations."""
    
    def __init__(self, config):
        """Initialize modpack manager.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.modpacks_dir = os.path.join("data", "modpacks")
        self.mod_manager = ModManager(config)
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Ensure required directories exist."""
        os.makedirs(self.modpacks_dir, exist_ok=True)
        
    def get_installed_modpacks(self) -> List[Modpack]:
        """Get list of installed modpacks.
        
        Returns:
            List[Modpack]: List of installed modpacks.
        """
        modpacks = []
        
        # For each modpack directory
        for modpack_id in os.listdir(self.modpacks_dir):
            modpack_dir = os.path.join(self.modpacks_dir, modpack_id)
            if not os.path.isdir(modpack_dir):
                continue
                
            # Check for manifest
            manifest_path = os.path.join(modpack_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                logging.warning(f"No manifest found for modpack {modpack_id}")
                continue
                
            try:
                modpack = Modpack.from_json(manifest_path)
                modpack.install_path = modpack_dir
                modpacks.append(modpack)
            except Exception as e:
                logging.error(f"Failed to load modpack {modpack_id}: {e}")
                
        return modpacks
        
    def install_modpack(self, modpack_path: str) -> Optional[Modpack]:
        """Install modpack from ZIP file.
        
        Args:
            modpack_path (str): Path to modpack ZIP file.
            
        Returns:
            Optional[Modpack]: Installed modpack or None if installation failed.
        """
        try:
            # Extract modpack to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(modpack_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    
                # Look for manifest.json
                manifest_path = os.path.join(temp_dir, "manifest.json")
                if not os.path.exists(manifest_path):
                    logging.error(f"No manifest found in modpack {modpack_path}")
                    return None
                    
                # Load modpack
                modpack = Modpack.from_json(manifest_path)
                
                # Create modpack directory
                modpack_dir = os.path.join(self.modpacks_dir, modpack.id)
                if os.path.exists(modpack_dir):
                    logging.warning(f"Modpack {modpack.id} already exists, removing...")
                    shutil.rmtree(modpack_dir)
                    
                # Copy modpack files
                shutil.copytree(temp_dir, modpack_dir)
                
                # Download mods
                mods_dir = os.path.join(modpack_dir, "mods")
                os.makedirs(mods_dir, exist_ok=True)
                
                for mod_info in modpack.mods:
                    mod = Mod(
                        id=mod_info.get("id"),
                        name=mod_info.get("name"),
                        version=mod_info.get("version"),
                        mc_versions=mod_info.get("mc_versions", []),
                        download_url=mod_info.get("download_url"),
                        file_name=mod_info.get("file_name"),
                        file_size=mod_info.get("file_size", 0),
                        file_hash=mod_info.get("file_hash"),
                        dependencies=mod_info.get("dependencies", [])
                    )
                    
                    if not self.mod_manager.download_mod(mod, mods_dir):
                        logging.warning(f"Failed to download mod {mod.name}")
                
                modpack.install_path = modpack_dir
                return modpack
                
        except Exception as e:
            logging.error(f"Failed to install modpack {modpack_path}: {e}")
            return None
            
    def uninstall_modpack(self, modpack: Modpack) -> bool:
        """Uninstall modpack.
        
        Args:
            modpack (Modpack): Modpack to uninstall.
            
        Returns:
            bool: True if uninstallation was successful, False otherwise.
        """
        if not modpack.is_installed:
            logging.warning(f"Modpack {modpack.name} is not installed")
            return False
            
        try:
            shutil.rmtree(modpack.install_path)
            logging.info(f"Modpack {modpack.name} uninstalled")
            return True
        except Exception as e:
            logging.error(f"Failed to uninstall modpack {modpack.name}: {e}")
            return False
            
    def update_modpack(self, modpack: Modpack, update_file: str) -> Optional[Modpack]:
        """Update modpack.
        
        Args:
            modpack (Modpack): Modpack to update.
            update_file (str): Path to update ZIP file.
            
        Returns:
            Optional[Modpack]: Updated modpack or None if update failed.
        """
        # Backup existing modpack
        backup_dir = f"{modpack.install_path}_backup"
        try:
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(modpack.install_path, backup_dir)
            
            # Uninstall existing modpack
            self.uninstall_modpack(modpack)
            
            # Install updated modpack
            updated_modpack = self.install_modpack(update_file)
            if updated_modpack:
                # Remove backup
                shutil.rmtree(backup_dir)
                return updated_modpack
            else:
                # Restore backup
                if os.path.exists(modpack.install_path):
                    shutil.rmtree(modpack.install_path)
                shutil.copytree(backup_dir, modpack.install_path)
                shutil.rmtree(backup_dir)
                logging.error(f"Failed to update modpack {modpack.name}, restored backup")
                return modpack
                
        except Exception as e:
            logging.error(f"Failed to update modpack {modpack.name}: {e}")
            # Try to restore backup if possible
            if os.path.exists(backup_dir) and not os.path.exists(modpack.install_path):
                shutil.copytree(backup_dir, modpack.install_path)
            # Clean up backup
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            return None
            
    def create_modpack(self, name: str, version: str, mc_versions: List[str],
                      author: str, description: str, icon_path: Optional[str] = None) -> Modpack:
        """Create a new modpack.
        
        Args:
            name (str): Modpack name.
            version (str): Modpack version.
            mc_versions (List[str]): Compatible Minecraft versions.
            author (str): Modpack author.
            description (str): Modpack description.
            icon_path (Optional[str]): Path to modpack icon.
            
        Returns:
            Modpack: Created modpack.
        """
        # Generate a safe ID from name
        modpack_id = name.lower().replace(" ", "_").replace("-", "_")
        # Add uniqueness using timestamp
        import time
        modpack_id = f"{modpack_id}_{int(time.time())}"
        
        # Create modpack object
        modpack = Modpack(
            id=modpack_id,
            name=name,
            version=version,
            mc_versions=mc_versions,
            author=author,
            description=description,
            icon_path=icon_path,
            mods=[],
            config_files=[],
            resource_packs=[]
        )
        
        # Create modpack directory
        modpack_dir = os.path.join(self.modpacks_dir, modpack_id)
        os.makedirs(modpack_dir, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(modpack_dir, "mods"), exist_ok=True)
        os.makedirs(os.path.join(modpack_dir, "config"), exist_ok=True)
        os.makedirs(os.path.join(modpack_dir, "resourcepacks"), exist_ok=True)
        
        # Save manifest
        manifest_path = os.path.join(modpack_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(modpack.to_dict(), f, indent=4)
            
        modpack.install_path = modpack_dir
        return modpack
        
    def export_modpack(self, modpack: Modpack, export_path: str) -> bool:
        """Export modpack to ZIP file.
        
        Args:
            modpack (Modpack): Modpack to export.
            export_path (str): Path to export ZIP file.
            
        Returns:
            bool: True if export was successful, False otherwise.
        """
        if not modpack.is_installed:
            logging.warning(f"Modpack {modpack.name} is not installed")
            return False
            
        try:
            with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add all files from modpack directory
                for root, _, files in os.walk(modpack.install_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, modpack.install_path)
                        zipf.write(file_path, arcname)
                        
            logging.info(f"Modpack {modpack.name} exported to {export_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to export modpack {modpack.name}: {e}")
            return False
            
    def check_for_updates(self, modpack: Modpack) -> Optional[Dict[str, Any]]:
        """Check for modpack updates.
        
        Args:
            modpack (Modpack): Modpack to check.
            
        Returns:
            Optional[Dict[str, Any]]: Update information or None if no update available.
        """
        # In a real implementation, this would check a repository for updates
        # For now, just return None (no updates)
        return None
        
    def add_mod_to_modpack(self, modpack: Modpack, mod: Mod) -> bool:
        """Add mod to modpack.
        
        Args:
            modpack (Modpack): Modpack to add mod to.
            mod (Mod): Mod to add.
            
        Returns:
            bool: True if mod was added successfully, False otherwise.
        """
        if not modpack.is_installed:
            logging.warning(f"Modpack {modpack.name} is not installed")
            return False
            
        try:
            # Check if mod is already in modpack
            for mod_info in modpack.mods:
                if mod_info.get("id") == mod.id:
                    logging.warning(f"Mod {mod.name} already in modpack {modpack.name}")
                    return False
                    
            # Download mod
            mods_dir = os.path.join(modpack.install_path, "mods")
            if not self.mod_manager.download_mod(mod, mods_dir):
                logging.error(f"Failed to download mod {mod.name}")
                return False
                
            # Add mod to modpack manifest
            modpack.mods.append(mod.to_dict())
            
            # Save manifest
            manifest_path = os.path.join(modpack.install_path, "manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(modpack.to_dict(), f, indent=4)
                
            logging.info(f"Mod {mod.name} added to modpack {modpack.name}")
            return True
        except Exception as e:
            logging.error(f"Failed to add mod {mod.name} to modpack {modpack.name}: {e}")
            return False
            
    def remove_mod_from_modpack(self, modpack: Modpack, mod_id: str) -> bool:
        """Remove mod from modpack.
        
        Args:
            modpack (Modpack): Modpack to remove mod from.
            mod_id (str): ID of mod to remove.
            
        Returns:
            bool: True if mod was removed successfully, False otherwise.
        """
        if not modpack.is_installed:
            logging.warning(f"Modpack {modpack.name} is not installed")
            return False
            
        try:
            # Find mod in modpack
            mod_info = None
            for i, info in enumerate(modpack.mods):
                if info.get("id") == mod_id:
                    mod_info = info
                    modpack.mods.pop(i)
                    break
                    
            if not mod_info:
                logging.warning(f"Mod {mod_id} not found in modpack {modpack.name}")
                return False
                
            # Remove mod file
            file_name = mod_info.get("file_name")
            if file_name:
                mod_path = os.path.join(modpack.install_path, "mods", file_name)
                if os.path.exists(mod_path):
                    os.remove(mod_path)
                    
            # Save manifest
            manifest_path = os.path.join(modpack.install_path, "manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(modpack.to_dict(), f, indent=4)
                
            logging.info(f"Mod {mod_info.get('name', mod_id)} removed from modpack {modpack.name}")
            return True
        except Exception as e:
            logging.error(f"Failed to remove mod {mod_id} from modpack {modpack.name}: {e}")
            return False