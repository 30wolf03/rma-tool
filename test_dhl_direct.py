"""Direkter Test des DHL Label Tools mit detailliertem Error Handling."""

import sys
import os
import traceback
from PySide6.QtWidgets import QApplication

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dhl_tool():
    """Testet das DHL Tool direkt mit detailliertem Error Handling."""
    print("=" * 80)
    print("DIREKTER DHL TOOL TEST")
    print("=" * 80)
    
    try:
        print("1. Importiere Module...")
        from modules.dhl_label_tool.label_generator import DHLLabelGenerator
        from modules.dhl_label_tool.billbee_api import BillbeeAPI
        print("✓ Module erfolgreich importiert")
        
        print("\n2. Erstelle QApplication...")
        app = QApplication(sys.argv)
        print("✓ QApplication erstellt")
        
        print("\n3. Erstelle DHLLabelGenerator...")
        window = DHLLabelGenerator()
        print("✓ DHLLabelGenerator erstellt")
        
        print("\n4. Zeige Fenster...")
        window.show()
        print("✓ Fenster angezeigt")
        
        print("\n5. Starte Event Loop...")
        print("Fenster sollte jetzt sichtbar sein. Schließe es zum Beenden.")
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"✗ Import-Fehler: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"✗ Unerwarteter Fehler: {e}")
        traceback.print_exc()
    finally:
        print("\nTest beendet.")

if __name__ == "__main__":
    test_dhl_tool() 