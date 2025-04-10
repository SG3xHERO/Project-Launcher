# filepath: c:\Users\benfo\Documents\Launcher\Project-Launcher\app\utils\java_utils.py
import shutil

def is_java_installed():
    """Check if Java is installed on the system."""
    return shutil.which("java") is not None