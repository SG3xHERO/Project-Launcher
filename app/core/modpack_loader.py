#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modpack management using launcher-lib for Project Launcher.
"""

import os
import sys
import json
import logging
import zipfile
import tempfile
import shutil
import hashlib
import subprocess
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from dataclasses import dataclass, field

import minecraft_launcher_lib


class Modpack:
    """Class representing a modpack."""
    
    def __init__(self):
        """Initialize Modpack."""
        self.id = ""
        self.name = ""
        self.version = ""
        self.mc_versions = []
        self.author = ""
        self.description = ""
        self.loader_type = ""  # forge or fabric
        self.mods = []
        self.config_files = []
        self.resource_packs = []
        self.install_path = None
        
        # Server-specific attributes
        self.download_url = ""
        self.file_size = 0
        self.file_hash = ""
        self.icon_url = ""
        self.download_count = 0
        self.is_server_pack = False
        self.mod_count = 0

    @classmethod
    def from_json(cls, json_path):
        """Create Modpack from JSON file.
        
        Args:
            json_path (str): Path to JSON file.
            
        Returns:
            Modpack: Modpack object.
        """
        modpack = cls()
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            # Check if this is a server format or client format
            if isinstance(data, list):
                # Server format (list of modpacks)
                if data:
                    data = data[0]  # Take the first one
                else:
                    return modpack
            
            # Common fields
            modpack.id = str(data.get('id', ''))
            modpack.name = data.get('name', 'Unknown Pack')
            modpack.version = data.get('version', '1.0.0')
            modpack.mc_versions = data.get('mc_versions', [])
            modpack.author = data.get('author', 'Unknown')
            modpack.description = data.get('description', '')
            
            # Handle loader type field differences
            modpack.loader_type = data.get('loader_type', data.get('modloader', 'forge'))
            
            # Local-specific fields
            modpack.mods = data.get('mods', [])
            modpack.config_files = data.get('config_files', [])
            modpack.resource_packs = data.get('resource_packs', [])
            
            # Server-specific fields
            modpack.download_url = data.get('download_url', '')
            modpack.file_size = data.get('file_size', 0)
            modpack.file_hash = data.get('file_hash', '')
            modpack.icon_url = data.get('icon_url', '')
            modpack.download_count = data.get('download_count', 0)
            modpack.is_server_pack = bool(modpack.download_url)
            modpack.mod_count = data.get('mod_count', len(modpack.mods))
            
        except Exception as e:
            logging.error(f"Error parsing modpack JSON: {e}")
            
        return modpack

    def to_dict(self):
        """Convert Modpack to dict.
        
        Returns:
            dict: Modpack as dict.
        """
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'mc_versions': self.mc_versions,
            'author': self.author,
            'description': self.description,
            'loader_type': self.loader_type,
            'mods': self.mods,
            'config_files': self.config_files,
            'resource_packs': self.resource_packs
        }
    
    @property
    def is_installed(self):
        """Check if modpack is installed.
        
        Returns:
            bool: True if installed.
        """
        return self.install_path is not None and os.path.isdir(self.install_path)


class ModpackManager:
    """Manager for modpack operations using minecraft-launcher-lib."""
    
    def __init__(self, config, minecraft_launcher):
        """Initialize modpack manager.
        
        Args:
            config: Configuration instance.
            minecraft_launcher: MinecraftLauncher instance.
        """
        self.config = config
        self.minecraft_launcher = minecraft_launcher
        self.modpacks_dir = os.path.join("data", "modpacks")
        os.makedirs(self.modpacks_dir, exist_ok=True)
        
    def get_installed_modpacks(self) -> List[Modpack]:
        """Get list of installed modpacks.
        
        Returns:
            List[Modpack]: List of installed modpacks.
        """
        modpacks = []
        
        # For each modpack directory
        if os.path.exists(self.modpacks_dir):
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
                    # First verify the manifest is valid JSON
                    try:
                        with open(manifest_path, 'r') as f:
                            json_data = json.load(f)
                    except json.JSONDecodeError as json_err:
                        logging.error(f"Invalid JSON in manifest for {modpack_id}: {json_err}")
                        # Create a basic valid manifest
                        json_data = {
                            "id": modpack_id,
                            "name": modpack_id.replace("_", " ").title(),
                            "version": "1.0.0",
                            "mc_versions": ["1.19.4"],
                            "author": "Unknown",
                            "description": "Recovered modpack",
                            "loader_type": "forge",
                            "mods": [],
                            "config_files": [],
                            "resource_packs": []
                        }
                        # Save the fixed manifest
                        with open(manifest_path, 'w') as f:
                            json.dump(json_data, f, indent=4)
                        logging.info(f"Created recovery manifest for {modpack_id}")
                    
                    # Now load the modpack (either from the original or fixed manifest)
                    modpack = Modpack.from_json(manifest_path)
                    modpack.install_path = modpack_dir
                    
                    # Verify mods exist and update mod list
                    self._verify_and_update_modpack_mods(modpack)
                    
                    modpacks.append(modpack)
                except Exception as e:
                    logging.error(f"Failed to load modpack {modpack_id}: {e}")
                    
        return modpacks

    def _verify_and_update_modpack_mods(self, modpack: Modpack):
        """Verify and update mod list for a modpack.
        
        Args:
            modpack (Modpack): Modpack to update.
        """
        if not modpack.is_installed:
            return
            
        # Check mods directory
        mods_dir = os.path.join(modpack.install_path, "mods")
        if not os.path.exists(mods_dir):
            return
        
        # Get current mod files
        mod_files = [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
        
        # Update mod list if it's empty but mods are found
        if not modpack.mods and mod_files:
            logging.info(f"Found {len(mod_files)} mods for {modpack.name} but mod list was empty")
            for mod_file in mod_files:
                # Create basic mod info
                mod_info = {
                    "name": os.path.splitext(mod_file)[0].replace("-", " "),
                    "filename": mod_file,
                    "version": "Unknown",
                    "mc_versions": modpack.mc_versions
                }
                modpack.mods.append(mod_info)
            
            # Save updated manifest
            manifest_path = os.path.join(modpack.install_path, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(modpack.to_dict(), f, indent=4)
            logging.info(f"Updated mod list for {modpack.name}")
        
    def install_modpack(self, modpack_path: str, 
                        progress_callback=None) -> Optional[Modpack]:
        """Install modpack from ZIP file.
        
        Args:
            modpack_path (str): Path to modpack ZIP file.
            progress_callback: Callback function for progress reporting.
            
        Returns:
            Optional[Modpack]: Installed modpack or None if installation failed.
        """
        try:
            # Create a default progress callback if none provided
            if progress_callback is None:
                def default_callback(progress, status):
                    logging.info(f"Installing modpack: {progress:.0%} - {status}")
                progress_callback = default_callback
            
            progress_callback(0.1, "Extracting modpack...")
            
            # Extract modpack to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(modpack_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    
                # Look for manifest.json
                manifest_path = os.path.join(temp_dir, "manifest.json")
                if not os.path.exists(manifest_path):
                    # Try to search for it recursively (some modpacks have different structures)
                    for root, _, files in os.walk(temp_dir):
                        if "manifest.json" in files:
                            manifest_path = os.path.join(root, "manifest.json")
                            break
                
                if not os.path.exists(manifest_path):
                    logging.error(f"No manifest found in modpack {modpack_path}")
                    progress_callback(1.0, "Error: No manifest found")
                    return None
                    
                progress_callback(0.2, "Reading manifest...")
                
                # Load modpack
                modpack = Modpack.from_json(manifest_path)
                
                # Create modpack directory
                modpack_dir = os.path.join(self.modpacks_dir, modpack.id)
                if os.path.exists(modpack_dir):
                    logging.warning(f"Modpack {modpack.id} already exists, removing...")
                    shutil.rmtree(modpack_dir)
                
                progress_callback(0.3, "Installing Minecraft version...")
                
                # Install Minecraft version if needed
                mc_version = modpack.mc_versions[0] if modpack.mc_versions else "1.19.4"
                if not minecraft_launcher_lib.utils.is_version_valid(
                        minecraft_launcher_lib.utils.get_minecraft_directory(), 
                        mc_version):
                    def mc_callback(current, total, status):
                        if total > 0:
                            install_progress = current / total
                            # Scale progress between 30% and 60%
                            overall_progress = 0.3 + (install_progress * 0.3)
                            progress_callback(overall_progress, f"Installing Minecraft {mc_version}: {status}")
                    
                    minecraft_launcher_lib.installer.install_minecraft_version(
                        mc_version,
                        minecraft_launcher_lib.utils.get_minecraft_directory(),
                        callback=mc_callback
                    )
                else:
                    progress_callback(0.6, f"Minecraft {mc_version} already installed")
                
                # Install mod loader if specified
                if modpack.loader_type and modpack.loader_type != "vanilla":
                    progress_callback(0.6, f"Installing {modpack.loader_type.capitalize()}...")
                    
                    if modpack.loader_type.lower() == "forge" and modpack.loader_version:
                        try:
                            forge_version = modpack.loader_version
                            
                            def forge_callback(current, total, status):
                                if total > 0:
                                    install_progress = current / total
                                    # Scale progress between 60% and 80%
                                    overall_progress = 0.6 + (install_progress * 0.2)
                                    progress_callback(overall_progress, f"Installing Forge {forge_version}: {status}")
                            
                            # Check if specific Forge version is valid
                            forge_info = minecraft_launcher_lib.forge.find_forge_version(mc_version, forge_version)
                            if not forge_info:
                                # Try to get latest compatible Forge version
                                forge_versions = minecraft_launcher_lib.forge.list_forge_versions()
                                compatible_versions = [v for v in forge_versions if v.startswith(f"{mc_version}-")]
                                if compatible_versions:
                                    forge_version = compatible_versions[0].split("-", 1)[1]
                                    logging.info(f"Using Forge version {forge_version} for Minecraft {mc_version}")
                                
                            minecraft_launcher_lib.forge.install_forge_version(
                                f"{mc_version}-{forge_version}",
                                minecraft_launcher_lib.utils.get_minecraft_directory(),
                                callback=forge_callback
                            )
                        except Exception as e:
                            logging.error(f"Failed to install Forge: {e}")
                            # Continue with installation anyway
                    
                    elif modpack.loader_type.lower() == "fabric":
                        try:
                            def fabric_callback(current, total, status):
                                if total > 0:
                                    install_progress = current / total
                                    # Scale progress between 60% and 80%
                                    overall_progress = 0.6 + (install_progress * 0.2)
                                    progress_callback(overall_progress, f"Installing Fabric: {status}")
                            
                            minecraft_launcher_lib.fabric.install_fabric(
                                mc_version,
                                minecraft_launcher_lib.utils.get_minecraft_directory(),
                                callback=fabric_callback
                            )
                        except Exception as e:
                            logging.error(f"Failed to install Fabric: {e}")
                            # Continue with installation anyway
                
                # Copy modpack files
                progress_callback(0.8, "Installing modpack files...")
                
                # Create modpack directory structure
                os.makedirs(modpack_dir, exist_ok=True)
                os.makedirs(os.path.join(modpack_dir, "mods"), exist_ok=True)
                os.makedirs(os.path.join(modpack_dir, "config"), exist_ok=True)
                os.makedirs(os.path.join(modpack_dir, "resourcepacks"), exist_ok=True)
                
                # Copy the manifest
                shutil.copy2(manifest_path, os.path.join(modpack_dir, "manifest.json"))
                
                # Copy mods
                mods_dir_source = os.path.join(os.path.dirname(manifest_path), "mods")
                if os.path.exists(mods_dir_source):
                    for item in os.listdir(mods_dir_source):
                        src_path = os.path.join(mods_dir_source, item)
                        if os.path.isfile(src_path):
                            shutil.copy2(src_path, os.path.join(modpack_dir, "mods", item))
                
                # Copy config files
                config_dir_source = os.path.join(os.path.dirname(manifest_path), "config")
                if os.path.exists(config_dir_source):
                    for root, dirs, files in os.walk(config_dir_source):
                        rel_path = os.path.relpath(root, config_dir_source)
                        dest_dir = os.path.join(modpack_dir, "config", rel_path)
                        os.makedirs(dest_dir, exist_ok=True)
                        
                        for file in files:
                            src_file = os.path.join(root, file)
                            dest_file = os.path.join(dest_dir, file)
                            shutil.copy2(src_file, dest_file)
                
                # Copy resource packs
                resource_dir_source = os.path.join(os.path.dirname(manifest_path), "resourcepacks")
                if os.path.exists(resource_dir_source):
                    for item in os.listdir(resource_dir_source):
                        src_path = os.path.join(resource_dir_source, item)
                        if os.path.isfile(src_path):
                            shutil.copy2(src_path, os.path.join(modpack_dir, "resourcepacks", item))
                
                # Copy icon if available
                icon_file = next((f for f in os.listdir(temp_dir) if f.endswith((".png", ".jpg", ".jpeg")) and "icon" in f.lower()), None)
                if icon_file:
                    src_path = os.path.join(temp_dir, icon_file)
                    dest_path = os.path.join(modpack_dir, "icon.png")
                    shutil.copy2(src_path, dest_path)
                    modpack.icon_path = dest_path
                
                progress_callback(1.0, "Installation complete!")
                
                # Update modpack with installation path
                modpack.install_path = modpack_dir
                
                # Save updated manifest
                with open(os.path.join(modpack_dir, "manifest.json"), "w") as f:
                    json.dump(modpack.to_dict(), f, indent=4)
                
                return modpack
                
        except Exception as e:
            logging.error(f"Failed to install modpack {modpack_path}: {e}")
            if progress_callback:
                progress_callback(1.0, f"Error: {str(e)}")
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
    
    def create_modpack(self, name: str, version: str, mc_versions: List[str],
                      author: str, description: str, 
                      loader_type: str = "forge", loader_version: Optional[str] = None,
                      icon_path: Optional[str] = None) -> Modpack:
        """Create a new modpack.
        
        Args:
            name (str): Modpack name.
            version (str): Modpack version.
            mc_versions (List[str]): Compatible Minecraft versions.
            author (str): Modpack author.
            description (str): Modpack description.
            loader_type (str): Mod loader type ("forge", "fabric", or "vanilla").
            loader_version (Optional[str]): Mod loader version.
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
        modpack = Modpack()
        modpack.id = modpack_id
        modpack.name = name
        modpack.version = version
        modpack.mc_versions = mc_versions
        modpack.author = author
        modpack.description = description
        modpack.loader_type = loader_type
        modpack.loader_version = loader_version
        modpack.icon_path = icon_path
        modpack.mods = []
        modpack.config_files = []
        modpack.resource_packs = []
        
        # Create modpack directory
        modpack_dir = os.path.join(self.modpacks_dir, modpack_id)
        os.makedirs(modpack_dir, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(modpack_dir, "mods"), exist_ok=True)
        os.makedirs(os.path.join(modpack_dir, "config"), exist_ok=True)
        os.makedirs(os.path.join(modpack_dir, "resourcepacks"), exist_ok=True)
        
        # Copy icon if provided
        if icon_path and os.path.exists(icon_path):
            icon_ext = os.path.splitext(icon_path)[1]
            dest_icon_path = os.path.join(modpack_dir, f"icon{icon_ext}")
            shutil.copy2(icon_path, dest_icon_path)
            modpack.icon_path = dest_icon_path
        
        # Save manifest
        manifest_path = os.path.join(modpack_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(modpack.to_dict(), f, indent=4)
            
        modpack.install_path = modpack_dir
        return modpack
    
    def update_modpack(self, modpack: Modpack, update_file: str,
                      progress_callback=None) -> Optional[Modpack]:
        """Update modpack from file.
        
        Args:
            modpack (Modpack): Modpack to update.
            update_file (str): Path to update ZIP file.
            progress_callback: Callback function for progress reporting.
            
        Returns:
            Optional[Modpack]: Updated modpack or None if update failed.
        """
        if not modpack.is_installed:
            logging.warning(f"Modpack {modpack.name} is not installed")
            return None
        
        # Backup existing modpack
        backup_dir = f"{modpack.install_path}_backup"
        try:
            # Create backup
            if progress_callback:
                progress_callback(0.1, "Creating backup...")
            
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(modpack.install_path, backup_dir)
            
            # Uninstall existing modpack
            if progress_callback:
                progress_callback(0.3, "Removing old version...")
            
            self.uninstall_modpack(modpack)
            
            # Install updated modpack
            if progress_callback:
                def update_progress(progress, status):
                    # Scale progress to 30%-90% range
                    overall_progress = 0.3 + (progress * 0.6)
                    progress_callback(overall_progress, status)
            else:
                update_progress = None
            
            updated_modpack = self.install_modpack(update_file, update_progress)
            
            if updated_modpack:
                # Remove backup
                if progress_callback:
                    progress_callback(0.95, "Cleaning up...")
                
                shutil.rmtree(backup_dir)
                
                if progress_callback:
                    progress_callback(1.0, "Update complete!")
                
                return updated_modpack
            else:
                # Restore backup
                if progress_callback:
                    progress_callback(0.8, "Update failed, restoring backup...")
                
                if os.path.exists(modpack.install_path):
                    shutil.rmtree(modpack.install_path)
                shutil.copytree(backup_dir, modpack.install_path)
                shutil.rmtree(backup_dir)
                
                if progress_callback:
                    progress_callback(1.0, "Restore complete")
                
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
            
            if progress_callback:
                progress_callback(1.0, f"Error: {str(e)}")
            
            return None
    
    def launch_modpack(self, modpack: Modpack, auth_manager, callback: Optional[Callable[[str], None]] = None) -> subprocess.Popen:
        """Launch Minecraft with the modpack.
        
        Args:
            modpack (Modpack): Modpack to launch.
            auth_manager: Authentication manager with user's credentials.
            callback (Optional[Callable[[str], None]]): Callback for log output.
            
        Returns:
            subprocess.Popen: Process object for the launched game.
        """
        if not modpack.is_installed:
            raise ValueError(f"Modpack {modpack.name} is not installed")
        
        if not auth_manager.is_logged_in():
            raise ValueError("User is not authenticated. Please login first.")
        
        # Determine version to launch
        mc_version = modpack.mc_versions[0] if modpack.mc_versions else "1.19.4"
        version_id = mc_version
        
        # Check if we should use a modloader version
        if modpack.loader_type == "forge" and modpack.loader_version:
            forge_version = f"{mc_version}-{modpack.loader_version}"
            if minecraft_launcher_lib.utils.is_version_valid(
                    minecraft_launcher_lib.utils.get_minecraft_directory(), 
                    forge_version):
                version_id = forge_version
            else:
                # Try to find any compatible forge version
                compatible_versions = [
                    v for v in minecraft_launcher_lib.utils.get_installed_versions(
                        minecraft_launcher_lib.utils.get_minecraft_directory()
                    ) if v.get("id", "").startswith(f"{mc_version}-forge-")
                ]
                if compatible_versions:
                    version_id = compatible_versions[0].get("id")
        
        elif modpack.loader_type == "fabric":
            # Try to find fabric version
            fabric_versions = [
                v for v in minecraft_launcher_lib.utils.get_installed_versions(
                    minecraft_launcher_lib.utils.get_minecraft_directory()
                ) if v.get("id", "").startswith(f"fabric-loader-") and mc_version in v.get("id", "")
            ]
            if fabric_versions:
                version_id = fabric_versions[0].get("id")
        
        # Build options
        options = {
            # JVM arguments
            "jvmArguments": self.minecraft_launcher.java_args.split(),
            
            # Game directory - use modpack directory
            "gameDirectory": modpack.install_path,
            
            # Disable Forge's display dialog
            "launcherName": "Project Launcher",
            "launcherVersion": "1.0.0"
        }
        
        try:
            # Generate the command
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                version=version_id,
                minecraft_directory=minecraft_launcher_lib.utils.get_minecraft_directory(),
                options=options,
                username=auth_manager.get_username(),
                uuid=auth_manager.get_uuid(),
                token=auth_manager.auth_data.get("access_token")
            )
            
            logging.info(f"Launching modpack {modpack.name} with version {version_id}")
            
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
            logging.error(f"Failed to launch modpack {modpack.name}: {e}")
            raise

    def load_server_modpacks(self) -> List[Modpack]:
        """Load modpacks from server's modpacks.json file.
        
        Returns:
            List[Modpack]: List of server modpacks.
        """
        modpacks = []
        server_modpacks_path = os.path.join(self.config.get('server_data_dir', 'server_data'), 'modpacks.json')
        
        if not os.path.exists(server_modpacks_path):
            logging.warning(f"Server modpacks file not found: {server_modpacks_path}")
            return modpacks
            
        try:
            with open(server_modpacks_path, 'r') as f:
                server_modpacks_data = json.load(f)
                
            for pack_data in server_modpacks_data:
                try:
                    # Convert server format to client format
                    modpack = Modpack()
                    modpack.id = str(pack_data.get('id', ''))
                    modpack.name = pack_data.get('name', 'Unknown Pack')
                    modpack.version = pack_data.get('version', '1.0.0')
                    modpack.mc_versions = pack_data.get('mc_versions', [])
                    modpack.author = pack_data.get('author', 'Unknown')
                    modpack.description = pack_data.get('description', '')
                    
                    # Convert modloader to loader_type
                    modpack.loader_type = pack_data.get('modloader', 'forge')
                    
                    # Server-specific fields
                    modpack.download_url = pack_data.get('download_url', '')
                    modpack.file_size = pack_data.get('file_size', 0)
                    modpack.file_hash = pack_data.get('file_hash', '')
                    modpack.icon_url = pack_data.get('icon_url', '')
                    modpack.download_count = pack_data.get('download_count', 0)
                    modpack.is_server_pack = True
                    
                    # Placeholder for mods - will be populated after download
                    modpack.mods = []
                    modpack.mod_count = pack_data.get('mod_count', 0)
                    
                    modpacks.append(modpack)
                    
                except Exception as e:
                    logging.error(f"Error parsing server modpack: {e}")
                    
        except Exception as e:
            logging.error(f"Failed to load server modpacks: {e}")
            
        return modpacks