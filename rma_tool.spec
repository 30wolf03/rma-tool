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
