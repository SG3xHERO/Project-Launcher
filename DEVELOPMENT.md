# Project Launcher - Development Guide

This document provides guidance for developers who want to contribute to or extend the Project Launcher for Minecraft modpacks.

## Development Environment Setup

### Required Software

1. **Python 3.9+** - The core programming language
2. **Git** - For version control
3. **IDE** - Recommended: Visual Studio Code or PyCharm

### Setting Up

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/project-launcher.git
   cd project-launcher
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Includes development tools
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

## Project Architecture

The launcher follows a modular architecture to make it easier to understand and extend:

### Core Components

1. **Minecraft Instance Management** (`app/core/minecraft.py`)
   - Handles Minecraft version detection
   - Manages game launching
   - Controls Java settings

2. **Modpack Management** (`app/core/modpack.py`)
   - Installs, updates, and removes modpacks
   - Manages modpack metadata
   - Handles export and import

3. **Mod Management** (`app/core/mods.py`)
   - Downloads and validates mods
   - Checks for updates
   - Resolves dependencies

4. **Configuration** (`app/config.py`)
   - Manages user settings
   - Handles persistent storage

### UI Components

1. **Main Window** (`app/ui/main_window.py`)
   - Primary interface
   - Modpack list
   - Launch controls

2. **Modpack Manager** (`app/ui/modpack_manager.py`)
   - Interface for managing individual modpacks
   - Mod list and actions
   - Configuration options

3. **Settings Dialog** (`app/ui/settings_dialog.py`)
   - User preferences
   - Java configuration
   - Download settings

4. **Resource Management** (various UI files)
   - Icons and images
   - Style sheets

## Extending the Launcher

### Adding a New Feature

1. **Identify where the feature belongs**:
   - Is it a core functionality or UI enhancement?
   - Which existing module should it extend?

2. **Implement the backend functionality first**:
   - Add methods to the relevant core classes
   - Ensure proper error handling
   - Add appropriate logging

3. **Create or update UI components**:
   - Extend existing UI classes as needed
   - Maintain consistent styling
   - Connect UI elements to backend functions

4. **Update documentation**:
   - Add comments to your code
   - Update the README if necessary
   - Consider adding user-facing help

### Example: Adding a New Mod Repository

1. **Extend the `ModManager` class**:
   ```python
   # In app/core/mods.py
   def add_repository(self, name, url):
       """Add a new mod repository.
       
       Args:
           name (str): Repository name.
           url (str): Repository URL.
           
       Returns:
           bool: True if repository was added successfully.
       """
       # Implementation here
   ```

2. **Add UI in the Settings Dialog**:
   ```python
   # In app/ui/settings_dialog.py
   # In the init_ui method:
   self.repo_list = QListWidget()
   repo_layout.addWidget(self.repo_list)
   
   add_repo_btn = QPushButton("Add Repository")
   add_repo_btn.clicked.connect(self.add_repository)
   repo_layout.addWidget(add_repo_btn)
   ```

3. **Connect the backend to the UI**:
   ```python
   # In app/ui/settings_dialog.py
   def add_repository(self):
       """Add a new repository."""
       name, ok1 = QInputDialog.getText(self, "Repository Name", "Enter repository name:")
       if ok1 and name:
           url, ok2 = QInputDialog.getText(self, "Repository URL", "Enter repository URL:")
           if ok2 and url:
               if self.mod_manager.add_repository(name, url):
                   self.load_repositories()
   ```

## Code Style Guidelines

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code style
- Use descriptive variable and function names
- Add docstrings to all functions and classes
- Keep functions focused on a single responsibility
- Use type hints for function parameters and return values

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_modpack.py

# Run with coverage report
pytest --cov=app
```

### Writing Tests

1. **Create test files** in the `tests/` directory
2. **Name test files** with a `test_` prefix
3. **Write test functions** that start with `test_`
4. **Use assertions** to verify expected behavior

Example:
```python
# tests/test_modpack.py
def test_modpack_creation():
    """Test creating a new modpack."""
    config = MockConfig()
    manager = ModpackManager(config)
    
    modpack = manager.create_modpack(
        name="Test Pack",
        version="1.0",
        mc_versions=["1.19.4"],
        author="Tester",
        description="Test modpack"
    )
    
    assert modpack.name == "Test Pack"
    assert modpack.version == "1.0"
    assert "1.19.4" in modpack.mc_versions
    assert modpack.is_installed
```

## Building for Distribution

### Creating Executables

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Build the executable**:
   ```bash
   # Windows
   pyinstaller --onefile --windowed --icon=app/ui/resources/icon.ico --name=ProjectLauncher main.py
   
   # macOS
   pyinstaller --onefile --windowed --icon=app/ui/resources/icon.icns --name=ProjectLauncher main.py
   
   # Linux
   pyinstaller --onefile --windowed --icon=app/ui/resources/icon.png --name=ProjectLauncher main.py
   ```

3. **Test the executable** thoroughly before distribution

### Creating Installers

- **Windows**: Use [NSIS](https://nsis.sourceforge.io/) or [Inno Setup](https://jrsoftware.org/isinfo.php)
- **macOS**: Create a DMG or use [create-dmg](https://github.com/sindresorhus/create-dmg)
- **Linux**: Create DEB or RPM packages using tools like [fpm](https://github.com/jordansissel/fpm)

## Best Practices

1. **Log extensively**:
   - Use the `logging` module
   - Log at appropriate levels
   - Include relevant context

2. **Handle errors gracefully**:
   - Use try/except blocks
   - Provide user-friendly error messages
   - Log detailed error information

3. **Keep the UI responsive**:
   - Run long operations in background threads
   - Show progress indicators
   - Use QThread for heavy tasks

4. **User-centric design**:
   - Keep the interface simple
   - Provide helpful tooltips
   - Add confirmation for destructive actions

5. **Security first**:
   - Validate all external inputs
   - Verify file hashes
   - Use secure connections for downloads

## Common Challenges and Solutions

### Java Detection Issues

Problem: Java installations can vary widely across systems.

Solution:
```python
def find_java_installations():
    """Scan for Java installations in common locations."""
    installations = []
    
    # Common Java locations by platform
    if platform.system() == "Windows":
        search_paths = [
            "C:\\Program Files\\Java\\*\\bin\\java.exe",
            "C:\\Program Files (x86)\\Java\\*\\bin\\java.exe"
        ]
    elif platform.system() == "Darwin":  # macOS
        search_paths = [
            "/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java",
            "/System/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java"
        ]
    else:  # Linux
        search_paths = [
            "/usr/lib/jvm/*/bin/java",
            "/usr/java/*/bin/java"
        ]
    
    # Use glob to find matches
    import glob
    for path_pattern in search_paths:
        for java_path in glob.glob(path_pattern):
            if os.access(java_path, os.X_OK):
                installations.append(java_path)
    
    return installations
```

### Mod Compatibility

Problem: Mods may have complex version and dependency requirements.

Solution:
```python
def check_mod_compatibility(mod, minecraft_version, installed_mods):
    """Check if a mod is compatible with the current environment."""
    # Check Minecraft version compatibility
    if minecraft_version not in mod.mc_versions:
        return False, f"Mod requires Minecraft {', '.join(mod.mc_versions)}"
    
    # Check dependencies
    missing = []
    for dep_id in mod.dependencies:
        if dep_id not in installed_mods:
            missing.append(dep_id)
    
    if missing:
        return False, f"Missing dependencies: {', '.join(missing)}"
    
    return True, "Compatible"
```

## Contributing to the Project

1. **Fork the repository** on GitHub
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and commit them
4. **Write or update tests** for your changes
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create a Pull Request** against the main repository

## Useful Resources

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Minecraft Wiki](https://minecraft.fandom.com/wiki/Minecraft_Wiki)
- [Forge Documentation](https://mcforge.readthedocs.io/en/latest/)
- [Fabric Documentation](https://fabricmc.net/wiki/doku.php)

## Contact

If you have questions or need help, you can reach out through:
- GitHub Issues
- Discord server (link TBD)
- Email: yourname@example.com

Happy coding!