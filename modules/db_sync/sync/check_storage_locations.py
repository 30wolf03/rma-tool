import os
import sys
from pathlib import Path

# Füge das übergeordnete Verzeichnis zum Python-Pfad hinzu
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent))

# Jetzt können wir die Module importieren
from database.connection import DatabaseConnection, DatabaseConnectionError
from utils.keepass_handler import KeepassHandler

def check_storage_locations(db_connection):
    """Liest alle Lagerorte aus der StorageLocations-Tabelle aus und gibt sie aus."""
    try:
        with db_connection.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ID, Name FROM StorageLocations ORDER BY ID;")
                rows = cursor.fetchall()
                print("\nAktuelle Lagerorte in der Datenbank:")
                print("-----------------------------------")
                for row in rows:
                    print(f"ID {row[0]}: {row[1]}")
                print("-----------------------------------\n")
    except Exception as e:
        print(f"Fehler beim Auslesen der Lagerorte: {e}")

if __name__ == "__main__":
    try:
        print(f"Aktuelles Arbeitsverzeichnis: {os.getcwd()}")
        print(f"Python-Pfad: {sys.path}")
        
        # KeePass-Handler initialisieren und Datenbankverbindung aufbauen
        keepass_handler = KeepassHandler("DiesIsDBSyncFürDasRMATool")
        db_connection = DatabaseConnection(keepass_handler)
        check_storage_locations(db_connection)
    except DatabaseConnectionError as e:
        print(f"Fehler beim Ausführen des Skripts: {e}")
    except Exception as e:
        print(f"Unerwarteter Fehler: {e}")
        print(f"Fehlertyp: {type(e)}")
        import traceback
        traceback.print_exc() 