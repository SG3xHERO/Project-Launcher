# filepath: c:\Users\benfo\Documents\Launcher\Project-Launcher\app\utils\memory_utils.py

import psutil

def get_memory_info():
    """Get total and available memory in MB."""
    memory = psutil.virtual_memory()
    return {"total": memory.total // (1024 * 1024), "available": memory.available // (1024 * 1024)}

def calculate_recommended_memory():
    """Calculate recommended memory allocation in MB."""
    memory_info = get_memory_info()
    return memory_info["available"] // 2  # Use half of available memory