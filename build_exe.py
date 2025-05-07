import re
import os
import shutil
import subprocess

def get_window_title():
    with open('label_generator.py', 'r', encoding='utf-8') as file:
        content = file.read()
        # Suche nach dem setWindowTitle Aufruf
        match = re.search(r'setWindowTitle\("([^"]+)"\)', content)
        if match:
            return match.group(1)
    return None

def clean_build_folders():
    # Lösche build und dist Ordner falls vorhanden
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    # Lösche .spec Dateien
    for file in os.listdir('.'):
        if file.endswith('.spec'):
            os.remove(file)

def main():
    # Hole den Fenstertitel
    window_title = get_window_title()
    if not window_title:
        print("Fehler: Konnte den Fenstertitel nicht finden!")
        return

    print(f"Gefundener Fenstertitel: {window_title}")
    
    # Lösche alte Build-Dateien
    clean_build_folders()

    # Erstelle PyInstaller Befehl
    cmd = [
        'pyinstaller',
        '--name', window_title,
        '--icon=icons/icon.ico',
        '--add-data', 'icons;icons',
        '--distpath', 'dist/_internals',
        'main.py'
    ]

    # Führe PyInstaller aus
    print("Starte PyInstaller...")
    subprocess.run(cmd)
    print("Build abgeschlossen!")

if __name__ == '__main__':
    main() 