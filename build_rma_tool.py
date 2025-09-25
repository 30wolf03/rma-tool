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

    # Clean up old spec files and executables in root
    old_files = [
        "main.spec",
        "rma_tool.spec",
        "RMA-Tool.exe",
        "DHL Label Tool 17.spec"
    ]
    for old_file in old_files:
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
                print(f"Removed old file: {old_file}")
            except Exception as e:
                print(f"Could not remove {old_file}: {e}")

    # Create PyInstaller spec
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

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

# Hidden imports for dynamic loading - only what's actually needed
hidden_imports = [
    "modules.dhl_label_tool.main",
    "modules.rma_db_gui.gui.main_window",
    "shared.credentials",
    "shared.utils",
    "pymysql",
    "paramiko",
    "pykeepass",
    "loguru",
    "requests",
]

# Include all PySide6 modules to ensure compatibility
hidden_imports += [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtSql",
    "PySide6.QtPrintSupport",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtConcurrent",
    "PySide6.QtTest",
    "PySide6.QtXml",
    "PySide6.QtXmlPatterns",
]

# Exclude only non-PySide6 modules to reduce size
excludes = [
    "tkinter",
    "unittest",
    "pydoc",
    "test",
    # Include all PySide6 modules - don't exclude any
]

# Add essential modules that are needed by dependencies
hidden_imports += [
    "pdb",  # Required by construct/pykeepass
    "construct",
    "construct.debug",
    "lxml",
    "lxml.etree",
    "lxml.objectify",
    "cryptography",
    "bcrypt",
    "nacl",
    "charset_normalizer",
    "certifi",
    "packaging",
    "setuptools",
    "pkg_resources",
    "platformdirs",
    "multiprocessing",
    "sqlite3",
    "ssl",
    "hashlib",
    "base64",
    "json",
    "xml",
    "urllib",
    "http",
]

# Only include essential data files
datas = [
    ("global_style.qss", "."),
    ("credentials.kdbx", "."),
    ("modules/dhl_label_tool/resources_rc.py", "modules/dhl_label_tool"),
    ("modules/dhl_label_tool/resources.py", "modules/dhl_label_tool"),
    ("modules/dhl_label_tool/resources.qrc", "modules/dhl_label_tool"),
    ("modules/dhl_label_tool/icons.py", "modules/dhl_label_tool"),
    ("resources", "resources"),
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
    excludes=excludes,
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
    strip=True,  # Strip debug symbols
    upx=True,    # Compress with UPX
    upx_exclude=[],  # Don't exclude anything from UPX
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons/dhl-label-tool-icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,  # Strip all binaries
    upx=True,
    upx_exclude=[],
    name='RMA-Tool',
    # Additional optimization
    optimize=2,  # Level 2 optimization
)

# Ensure output goes to dist directory
import shutil
if os.path.exists('RMA-Tool'):
    if not os.path.exists('dist'):
        os.makedirs('dist')
    shutil.move('RMA-Tool', 'dist/RMA-Tool')
    print("Moved build output to dist/RMA-Tool directory")
'''

    # Write spec file
    spec_file = project_root / "rma_tool.spec"
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    print(f"Created spec file: {spec_file}")

    # Run PyInstaller with explicit distpath
    print("Running PyInstaller...")
    success = run_command(f"python -m PyInstaller --clean -y --distpath {dist_dir} rma_tool.spec", cwd=project_root)

    if not success:
        print("PyInstaller failed!")
        return False

    # Check if executable was created in the correct location
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
        print("Executable not found in expected location!")
        # Check if it was created in root directory
        root_exe = project_root / "RMA-Tool.exe"
        if root_exe.exists():
            print(f"Found executable in root directory: {root_exe}")
            print("Moving to dist folder...")
            if not dist_dir.exists():
                dist_dir.mkdir()
            import shutil
            shutil.move(str(root_exe), str(exe_path))
            print(f"Moved to: {exe_path}")
            return True
        else:
            print("Executable not found anywhere!")
            return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nBuild completed successfully!")
        print("You can now distribute the RMA-Tool executable!")
    else:
        print("\nBuild failed!")
        sys.exit(1)