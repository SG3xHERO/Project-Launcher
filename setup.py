#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script for the Minecraft Modpack Launcher.
"""

import os
import sys
import platform
from setuptools import setup, find_packages

# Get version from package
sys.path.insert(0, os.path.abspath('.'))
from app import __version__  # noqa

# Get long description from README
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

# Additional options based on platform
platform_specific = {}

# PyInstaller spec file
pyinstaller_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ProjectLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
"""

# Platform-specific additions
if platform.system() == "Windows":
    pyinstaller_spec += """    icon='app/ui/resources/icon.ico',
)
"""
elif platform.system() == "Darwin":  # macOS
    pyinstaller_spec += """    icon='app/ui/resources/icon.icns',
)

app = BUNDLE(
    exe,
    name='ProjectLauncher.app',
    icon='app/ui/resources/icon.icns',
    bundle_identifier='com.yourcompany.projectlauncher',
)
"""
else:  # Linux
    pyinstaller_spec += """    icon='app/ui/resources/icon.png',
)
"""

# Write PyInstaller spec file
with open('projectlauncher.spec', 'w') as spec_file:
    spec_file.write(pyinstaller_spec)

setup(
    name="project-launcher",
    version=__version__,
    description="A lightweight, user-friendly Minecraft launcher with modpack management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/project-launcher",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "projectlauncher=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "PyQt6>=6.5.0",
        "requests>=2.30.0",
        "jsonschema>=4.17.3",
        "pillow>=9.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "pyinstaller>=5.10.0",
        ],
    },
    **platform_specific,
)