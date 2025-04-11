import os
import shutil

def copy_and_rename_py_files_to_folder(source_folder, target_folder):
    # Zielordner erstellen, falls er nicht existiert
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # Durch alle Dateien im Quellordner iterieren
    for filename in os.listdir(source_folder):
        # Prüfen ob die Datei mit .py endet
        if filename.endswith('.py') and filename != 'copy_to_txt.py' or filename.endswith('.qss') or filename.endswith('.qrc'):
            # Alte und neue Pfade erstellen
            old_path = os.path.join(source_folder, filename)
            new_path = os.path.join(target_folder, f"{filename}.txt")
            
            # Datei kopieren und umbenennen
            shutil.copy(old_path, new_path)
            print(f"Kopiert und umbenannt: {filename} -> {new_path}")

# Beispielaufruf
source_folder = "."  # Aktueller Ordner
target_folder = "converted_files"  # Zielordner
copy_and_rename_py_files_to_folder(source_folder, target_folder)