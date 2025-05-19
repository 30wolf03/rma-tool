import os
import sys
import subprocess
import shutil
from datetime import datetime

def get_window_title():
    """Liest den Fenstertitel aus der label_generator.py."""
    with open('label_generator.py', 'r', encoding='utf-8') as file:
        for line in file:
            if 'self.setWindowTitle' in line:
                # Extrahiere den Titel aus der Zeile
                title = line.split('"')[1]
                return title
    return "DHL Label Tool"

def main():
    # Hole den Fenstertitel
    window_title = get_window_title()
    
    # Erstelle die .spec-Datei
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icons', 'icons'),
        ('global_style.qss', '.'),
        ('DHL_Label_Generator_secrets.kdbx', '.'),
        ('resources.py', '.'),
        ('resources_rc.py', '.'),
        ('icons.py', '.'),
        ('helpers.py', '.'),
        ('login_window.py', '.'),
        ('label_generator.py', '.'),
        ('dhl_api.py', '.'),
        ('zendesk_api.py', '.'),
        ('utils.py', '.')
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'cryptography',
        'requests',
        'lxml',
        'argon2'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{window_title}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{window_title}',
)
"""
    
    # Schreibe die .spec-Datei
    spec_file = f'{window_title}.spec'
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    # Führe PyInstaller mit der .spec-Datei aus
    subprocess.run(['pyinstaller', spec_file])
    
    print(f"\nBuild abgeschlossen! Die Dateien befinden sich im Ordner: dist/{window_title}\n")

if __name__ == '__main__':
    main() 