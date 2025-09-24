#!/usr/bin/env python3
"""
Build script for RMA-Tool
Creates a standalone executable with PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"[OK] {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {command} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Build the RMA-Tool executable"""
    print("Building RMA-Tool executable...")

    # Get project root
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    # Clean previous builds
    if dist_dir.exists():
        print("Cleaning previous build...")
        run_command(f"rd /s /q {dist_dir}")
    if build_dir.exists():
        run_command(f"rd /s /q {build_dir}")

    # Create PyInstaller spec
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Add project root to path
import os
project_root = Path(os.path.dirname(os.path.abspath('.')))
sys.path.insert(0, str(project_root))

block_cipher = None

# Main script
import os
main_script = os.path.abspath("main.py")

# Hidden imports for dynamic loading
hidden_imports = [
    "modules.dhl_label_tool.main",
    "modules.rma_db_gui.gui.main_window",
    "shared.credentials",
    "shared.utils",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "pymysql",
    "paramiko",
    "pykeepass",
    "loguru",
    "requests",
    "packaging",
]

# Collect data files
datas = [
    ("global_style.qss", "."),
    ("modules/dhl_label_tool/resources_rc.py", "resources"),
    ("modules/dhl_label_tool/resources.py", "resources"),
    ("modules/dhl_label_tool/resources.qrc", "resources"),
    ("modules/dhl_label_tool/icons.py", "icons"),
    ("credentials.kdbx", "."),
    ("resources", "resources"),
    ("modules", "modules"),
    ("shared", "shared"),
]

# Collect all Python files
python_files = []
for root, dirs, files in os.walk(project_root):
    for file in files:
        if file.endswith('.py'):
            python_files.append(str(Path(root) / file))

a = Analysis(
    [main_script],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
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
    [],
    exclude_binaries=True,
    name='RMA-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RMA-Tool'
)
'''

    # Write spec file
    spec_file = project_root / "rma_tool.spec"
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    print(f"Created spec file: {spec_file}")

    # Run PyInstaller
    print("Running PyInstaller...")
    success = run_command(f"pyinstaller --clean -y rma_tool.spec", cwd=project_root)

    if not success:
        print("PyInstaller failed!")
        return False

    # Check if executable was created
    exe_path = dist_dir / "RMA-Tool" / "RMA-Tool.exe"
    if exe_path.exists():
        print(f"Executable created: {exe_path}")

        # Note: credentials.kdbx is now included in executable directory via datas
        print("Credentials.kdbx included in executable directory")

        print(f"Distribution folder: {dist_dir / 'RMA-Tool'}")

        # Create portable version info
        print("\nPortable Version Info:")
        print(f"   • Executable: {exe_path}")
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"   • Size: {size_mb:.1f} MB")
        print(f"   • Distribution: {dist_dir / 'RMA-Tool'}")

        return True
    else:
        print("Executable not found!")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nBuild completed successfully!")
        print("You can now distribute the RMA-Tool executable!")
    else:
        print("\nBuild failed!")
        sys.exit(1)