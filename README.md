# Project Launcher - Minecraft Modpack Manager

A lightweight, user-friendly Minecraft launcher with comprehensive modpack management capabilities, designed to make modded Minecraft more accessible to everyone.


## Features

- **Simple, Clean Interface**: Minimalist design focused on ease of use
- **Modpack Management**: One-click installation, updates, and mod management
- **Custom Modpack Creation**: Create and customize your own modpacks
- **Mod Compatibility Checking**: Verify mods are compatible before installation
- **Low Resource Usage**: Designed to be lightweight and efficient
- **Export & Sharing**: Easily export modpacks to share with friends
- **Version Management**: Support for multiple Minecraft versions
- **Secure Downloads**: Verification of mod sources and files

## Installation

### Prerequisites

- **Python 3.9 or higher**
- **Java 8 or higher** (for running Minecraft)

### Windows Installation

1. Download the latest release from the [Releases](https://github.com/yourusername/project-launcher/releases) page
2. Extract the ZIP file to a location of your choice
3. Run `ProjectLauncher.exe`

### Linux/macOS Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/project-launcher.git
   cd project-launcher
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the launcher:
   ```bash
   python main.py
   ```

## Development Setup

If you want to contribute to the project or build from source:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/project-launcher.git
   cd project-launcher
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Run the application:
   ```bash
   python main.py
   ```

### Building Executables

To build standalone executables:

```bash
# Windows
pyinstaller --onefile --windowed --icon=app/ui/resources/icon.ico main.py

# macOS
pyinstaller --onefile --windowed --icon=app/ui/resources/icon.icns main.py

# Linux
pyinstaller --onefile --windowed --icon=app/ui/resources/icon.png main.py
```

## Project Structure

```
minecraft_launcher/
├── main.py                      # Entry point
├── app/                         # Application code
│   ├── core/                    # Core functionality
│   │   ├── minecraft.py         # Minecraft instance management
│   │   ├── modpack.py           # Modpack management
│   │   └── mods.py              # Mod management
│   ├── ui/                      # User interface
│   └── data/                    # Data models
└── data/                        # Local data storage
```

## Usage Guide

### Installing a Modpack

1. Click "Install Modpack" on the main screen
2. Select a modpack from the repository or choose a local ZIP file
3. Click "Install" and wait for the process to complete
4. Once installed, select the modpack from the list and click "Launch Minecraft"

### Creating a Custom Modpack

1. Click "Create Modpack" on the main screen
2. Enter a name, version, and description for your modpack
3. Select a compatible Minecraft version
4. Add mods from the repository or from local files
5. Configure settings as needed
6. Click "Save" to create your modpack

### Managing Mods

1. Select a modpack from the list
2. Go to the "Mods" tab
3. Use the "Add Mod" button to add new mods
4. Select a mod and click "Remove Mod" to remove it
5. Click "Update Mod" to check for and install updates

### Exporting a Modpack

1. Select a modpack from the list
2. Click "Export Modpack"
3. Choose a location to save the ZIP file
4. Share the ZIP file with friends

## Contributing

We welcome contributions to Project Launcher! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

### Code Style

We follow PEP 8 guidelines for Python code style. Please ensure your code passes linting before submitting pull requests.

### Adding Features

If you'd like to add a new feature:

1. First check if there's an open issue discussing the feature
2. Create a new issue if one doesn't exist
3. Fork the repository and create a new branch for your feature
4. Implement the feature with appropriate tests
5. Submit a pull request referencing the issue

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The Minecraft community for inspiration
- All the mod developers who create amazing content
- Contributors who help improve this launcher

---

Project Launcher is not affiliated with Mojang Studios or Microsoft.
