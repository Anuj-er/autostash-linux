import PyInstaller.__main__
import os
import shutil

def build_executable():
    # Clean previous builds
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    # PyInstaller arguments
    args = [
        'main.py',  # Your main script
        '--name=autostash',  # Name of the executable
        '--onefile',  # Create a single executable
        '--windowed',  # Don't show console window
        '--add-data=styles.py:.',  # Include styles.py
        '--add-data=core:core',  # Include core directory
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Replace existing build
    ]

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    # Update desktop file with correct path
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=AutoStash
Comment=Linux Backup System
Exec={os.path.abspath('dist/autostash')}
Terminal=false
Categories=Utility;System;Backup;
Keywords=backup;system;linux;
StartupNotify=true
"""
    
    with open('autostash.desktop', 'w') as f:
        f.write(desktop_content)

    print("Build completed successfully!")
    print(f"Executable created at: {os.path.abspath('dist/autostash')}")

if __name__ == '__main__':
    build_executable() 