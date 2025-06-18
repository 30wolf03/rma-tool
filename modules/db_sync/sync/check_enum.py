"""Skript zum Überprüfen der ENUM-Werte der LastAction-Spalte."""

from __future__ import annotations

from ..database.connection import DatabaseConnection
from ..utils.keepass_handler import KeepassHandler

def main():
    """Hauptfunktion zum Überprüfen der ENUM-Werte."""
    try:
        password = input("Bitte KeePass Master-Passwort eingeben: ")
        keepass_handler = KeepassHandler(password)
        db_connection = DatabaseConnection(keepass_handler)
        
        with db_connection.get_connection() as conn:
            cursor = conn.cursor()
            
            # Hole die ENUM-Werte der LastAction-Spalte
            cursor.execute("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'RMA_RepairDetails' 
                AND COLUMN_NAME = 'LastAction'
            """)
            result = cursor.fetchone()
            if result:
                print("\nAktuelle ENUM-Werte für LastAction:")
                print(result[0])
            else:
                print("Spalte LastAction nicht gefunden!")
            
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    main() 