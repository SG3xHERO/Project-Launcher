"""
Minecraft launcher integration module.
"""
import os
import logging
import minecraft_launcher_lib

class MinecraftLauncher:
    """MinecraftLauncher class for managing Minecraft installation and launching."""
    
    def __init__(self, config, auth_manager):
        """Initialize the Minecraft launcher.
        
        Args:
            config: Application configuration.
            auth_manager: Authentication manager for Microsoft accounts.
        """
        self.config = config
        self.auth_manager = auth_manager
        
        # Get minecraft directory
        self.minecraft_dir = config.get("minecraft_directory", 
                                      os.path.join(os.path.expanduser("~"), ".minecraft"))
    
    def get_versions(self):
        """Get available Minecraft versions.
        
        Returns:
            list: List of available Minecraft versions.
        """
        return minecraft_launcher_lib.utils.get_version_list()
    
    def install_minecraft(self, version, callback=None):
        """Install a specific Minecraft version.
        
        Args:
            version: Minecraft version to install.
            callback: Progress callback function.
        """
        minecraft_launcher_lib.install.install_minecraft_version(
            version, self.minecraft_dir, callback=callback
        )
    
    def launch_minecraft(self, version, username=None, uuid=None, token=None):
        """Launch Minecraft with the specified version.
        
        Args:
            version: Minecraft version to launch.
            username: Player username.
            uuid: Player UUID.
            token: Authentication token.
            
        Returns:
            subprocess.Popen: Minecraft process.
        """
        # Get current auth details if not provided
        if not (username and uuid and token) and self.auth_manager.is_logged_in():
            profile = self.auth_manager.get_profile()
            username = profile.get("name")
            uuid = profile.get("id")
            token = profile.get("access_token")
        
        if not (username and uuid and token):
            raise ValueError("Authentication required to launch Minecraft")
        
        # Set launch options
        options = {
            "username": username,
            "uuid": uuid,
            "token": token,
            "launcherName": "Project Launcher",
            "launcherVersion": "1.0"
        }
        
        # Add JVM arguments if specified
        jvm_args = self.config.get("jvm_arguments", "")
        if jvm_args:
            options["jvmArguments"] = jvm_args.split(" ")
        
        # Add memory settings
        memory = self.config.get("memory", 2048)
        options["jvmArguments"] = options.get("jvmArguments", []) + [
            f"-Xmx{memory}M"
        ]
        
        # Launch Minecraft
        return minecraft_launcher_lib.command.launch_minecraft(
            self.minecraft_dir, version, options
        )