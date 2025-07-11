#!/usr/bin/env python3
"""Test-Script für das Log-Einstellungs-GUI."""

import sys
from pathlib import Path

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication, QDialog
    from shared.utils.logger import create_log_settings_dialog, show_log_statistics
    
    def test_log_gui():
        """Testet das Log-Einstellungs-GUI."""
        print("=== Log-Einstellungs-GUI Test ===")
        
        # Zeige aktuelle Statistiken
        print("\nAktuelle Log-Statistiken:")
        show_log_statistics()
        
        # Erstelle QApplication
        app = QApplication(sys.argv)
        
        # Erstelle und zeige Dialog
        dialog = create_log_settings_dialog()
        if dialog:
            print("\nGUI-Dialog wird angezeigt...")
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                print("Dialog wurde mit 'Speichern' geschlossen")
            else:
                print("Dialog wurde mit 'Abbrechen' geschlossen")
        else:
            print("Fehler: Dialog konnte nicht erstellt werden")
        
        app.quit()
        
    if __name__ == "__main__":
        test_log_gui()
        
except ImportError as e:
    print(f"Fehler beim Import: {e}")
    print("PySide6 ist möglicherweise nicht installiert.")
except Exception as e:
    print(f"Unerwarteter Fehler: {e}") 