#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility functions for the Minecraft Modpack Launcher.
"""

import os
import sys
import logging
import platform
import subprocess
import time
import re
import json
import hashlib
import shutil
from typing import Dict, Any, Optional, List, Tuple


def setup_logging(log_level=logging.INFO):
    """Set up logging configuration.
    
    Args:
        log_level: Logging level.
    """
    log_dir = os.path.join("data", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"launcher_{time.strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"Logging to {log_file}")
    logging.info(f"System: {platform.system()} {platform.release()}")
    logging.info(f"Python: {platform.python_version()}")


def ensure_directories():
    """Ensure required directories exist."""
    directories = [
        os.path.join("data"),
        os.path.join("data", "minecraft"),
        os.path.join("data", "modpacks"),
        os.path.join("data", "temp"),
        os.path.join("data", "logs")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.debug(f"Ensured directory: {directory}")


def is_java_installed() -> bool:
    """Check if Java is installed.
    
    Returns:
        bool: True if Java is installed, False otherwise.
    """
    try:
        if platform.system() == "Windows":
            cmd = ["java", "-version"]
        else:
            cmd = ["java", "-version"]
            
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            # Extract Java version from output
            version_pattern = r'version "([^"]+)"'
            version_match = re.search(version_pattern, result.stderr)
            
            if version_match:
                java_version = version_match.group(1)
                logging.info(f"Java version: {java_version}")
                return True
            else:
                logging.warning("Java is installed but version could not be determined")
                return True
        else:
            logging.warning("Java is not installed or not in PATH")
            return False
            
    except Exception as e:
        logging.error(f"Error checking Java installation: {e}")
        return False


def get_memory_info() -> Dict[str, int]:
    """Get system memory information.
    
    Returns:
        Dict[str, int]: Dictionary with total and available memory in MB.
    """
    total_memory = 0
    available_memory = 0
    
    try:
        if platform.system() == "Windows":
            import ctypes
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
                
                def __init__(self):
                    self.dwLength = ctypes.sizeof(self)
                    super().__init__()
            
            stat = MEMORYSTATUSEX()
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            
            total_memory = stat.ullTotalPhys // (1024 * 1024)  # Convert to MB
            available_memory = stat.ullAvailPhys // (1024 * 1024)  # Convert to MB
            
        elif platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                
                for line in lines:
                    if "MemTotal" in line:
                        total_memory = int(line.split()[1]) // 1024  # Convert from KB to MB
                    elif "MemAvailable" in line:
                        available_memory = int(line.split()[1]) // 1024  # Convert from KB to MB
                        
        elif platform.system() == "Darwin":  # macOS
            # Use subprocess to call vm_stat command
            result = subprocess.run(
                ["vm_stat"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                # Parse vm_stat output
                page_size = 4096  # Default page size in bytes
                
                # Extract total memory using sysctl
                sysctl_result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if sysctl_result.returncode == 0:
                    total_memory = int(sysctl_result.stdout.strip()) // (1024 * 1024)  # Convert to MB
                
                # Parse vm_stat output to get free pages
                free_pages = 0
                for line in result.stdout.splitlines():
                    if "Pages free" in line:
                        free_pages += int(line.split()[2].rstrip("."))
                    if "Pages inactive" in line:
                        free_pages += int(line.split()[2].rstrip("."))
                        
                available_memory = (free_pages * page_size) // (1024 * 1024)  # Convert to MB
                
    except Exception as e:
        logging.error(f"Error getting memory information: {e}")
        
    return {
        "total": total_memory,
        "available": available_memory
    }


def calculate_recommended_memory(memory_info: Dict[str, int]) -> str:
    """Calculate recommended memory allocation for Minecraft.
    
    Args:
        memory_info (Dict[str, int]): Memory information from get_memory_info().
        
    Returns:
        str: Recommended memory allocation in JVM format (e.g., "-Xmx4G").
    """
    total_mb = memory_info.get("total", 0)
    available_mb = memory_info.get("available", 0)
    
    # Use the minimum of 75% of total or available memory
    limit_mb = min(int(total_mb * 0.75), available_mb)
    
    # Ensure minimum 1GB, maximum 16GB
    limit_mb = max(1024, min(limit_mb, 16 * 1024))
    
    # Round to nearest GB
    limit_gb = round(limit_mb / 1024)
    limit_gb = max(1, limit_gb)
    
    return f"-Xmx{limit_gb}G"


def download_file(url: str, target_path: str, progress_callback=None) -> bool:
    """Download file with progress reporting.
    
    Args:
        url (str): URL to download.
        target_path (str): Path to save downloaded file.
        progress_callback: Callback function for progress reporting.
        
    Returns:
        bool: True if download was successful, False otherwise.
    """
    try:
        import requests
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Download file with progress reporting
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get content length if available
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
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
            
        return True
        
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        
        # Clean up partial download
        if os.path.exists(target_path):
            os.remove(target_path)
            
        return False


def calculate_checksum(file_path: str, algorithm: str = "sha256") -> Optional[str]:
    """Calculate file checksum.
    
    Args:
        file_path (str): Path to file.
        algorithm (str): Hash algorithm to use.
        
    Returns:
        Optional[str]: Calculated checksum or None if error.
    """
    try:
        hash_obj = None
        
        if algorithm.lower() == "sha256":
            hash_obj = hashlib.sha256()
        elif algorithm.lower() == "sha1":
            hash_obj = hashlib.sha1()
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
        logging.error(f"Failed to calculate checksum for {file_path}: {e}")
        return None


def extract_zip(zip_path: str, extract_path: str) -> bool:
    """Extract ZIP file.
    
    Args:
        zip_path (str): Path to ZIP file.
        extract_path (str): Path to extract to.
        
    Returns:
        bool: True if extraction was successful, False otherwise.
    """
    try:
        import zipfile
        
        os.makedirs(extract_path, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        return True
        
    except Exception as e:
        logging.error(f"Failed to extract {zip_path}: {e}")
        return False