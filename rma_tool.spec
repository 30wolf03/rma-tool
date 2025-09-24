
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
