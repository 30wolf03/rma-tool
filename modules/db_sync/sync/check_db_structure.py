"""Skript zum Überprüfen der Datenbankstruktur."""

from __future__ import annotations

from ..database.connection import DatabaseConnection
from ..utils.keepass_handler import KeepassHandler

def main():
    """Hauptfunktion zum Überprüfen der Datenbankstruktur."""
    try:
        # KeePass-Handler initialisieren
        password = input("Bitte KeePass Master-Passwort eingeben: ")
        keepass_handler = KeepassHandler(password)
        
        # Datenbankverbindung herstellen
        db_connection = DatabaseConnection(keepass_handler)
        
        # Tabellenstruktur abfragen
        with db_connection.get_connection() as conn:
            cursor = conn.cursor()
            
            # RMA_Cases Struktur
            print("\nRMA_Cases Struktur:")
            cursor.execute("DESCRIBE RMA_Cases")
            for row in cursor.fetchall():
                print(row)
            
            # RMA_Products Struktur
            print("\nRMA_Products Struktur:")
            cursor.execute("DESCRIBE RMA_Products")
            for row in cursor.fetchall():
                print(row)
            
            # RMA_RepairDetails Struktur
            print("\nRMA_RepairDetails Struktur:")
            cursor.execute("DESCRIBE RMA_RepairDetails")
            for row in cursor.fetchall():
                print(row)
            
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    main() 