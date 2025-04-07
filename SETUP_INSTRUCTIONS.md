# Project Launcher Setup Instructions

This document provides instructions for setting up and running the Project Launcher application.

## Project Structure

After setting up the project, you should have the following directory structure:

```
project-launcher/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── utils.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── java_installer.py
│   │   ├── minecraft.py
│   │   ├── minecraft_downloader.py
│   │   ├── modpack.py
│   │   ├── mods.py
│   │   ├── repository.py
│   │   └── security.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── install_dialog.py
│   │   ├── main_window.py
│   │   ├── modpack_browser.py
│   │   ├── modpack_manager.py
│   │   ├── settings_dialog.py
│   │   └── resources/
│   │       ├── icon.png
│   │       └── style.css
│   └── data/
│       ├── __init__.py
│       └── modpack.py
├── data/
│   ├── config.json
│   ├── logs/
│   ├── temp/
│   ├── modpacks/
│   ├── minecraft/
│   ├── java/
│   └── cache/
│       └── repositories/
├── main.py
├── setup.py
├── requirements.txt
├── README.md
├── GETTING_STARTED.md
├── DEVELOPMENT.md
└── SETUP_INSTRUCTIONS.md
```

## Setup Instructions

### 1. Set Up Python Environment

First, ensure you have Python 3.9 or newer installed. Then, set up a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

### 3. Create Directory Structure

Run the directory setup script to create all necessary folders and files:

```bash
python setup_directories.py
```

This will create:
- Required directory structure
- Default configuration file
- Application icon

### 4. Launch the Application

Now you can run the launcher:

```bash
python main.py
```

## First Run

When you first run the application:

1. It will prompt you to set up Java if none is detected
2. You'll need to install at least one Minecraft version through the Installation Manager
3. You can then install or create modpacks

## Troubleshooting

### Missing Modules

If you encounter "ModuleNotFoundError" messages, ensure you have:
- Activated the virtual environment
- Installed all dependencies via `pip install -r requirements.txt`

### Java Issues

If the launcher can't find Java:
1. Go to Tools → Installation Manager
2. Select the Java tab
3. Click "Install Java 21" or "Detect Java"

### Minecraft Installation Issues

If you have problems installing Minecraft:
1. Go to Tools → Installation Manager
2. Select the Minecraft tab
3. Select a version and click "Install"

## Development Setup

For development, you'll want to install additional packages:

```bash
pip install -e ".[dev]"
```

This installs development tools like pytest, flake8, and PyInstaller.

## Building Executable

To build a standalone executable:

```bash
# First generate the spec file
python setup.py build

# Then build the executable
pyinstaller projectlauncher.spec
```

The executable will be created in the `dist` directory.