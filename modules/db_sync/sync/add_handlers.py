"""Skript zum Hinzufügen der Handler aus der CSV-Datei zur Datenbank."""

from pathlib import Path
import csv
from typing import Set
import logging
import sys

from loguru import logger

from ..database.connection import DatabaseConnection, DatabaseConnectionError
from ..utils.keepass_handler import KeepassHandler

# Konfiguriere das Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def extract_handlers_from_csv(csv_path: Path) -> Set[str]:
    """Extrahiert alle einzigartigen Handler aus der CSV-Datei."""
    handlers = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                handler = row.get('letzter Bearbeiter', '').strip()
                if handler and handler != '-':
                    handlers.add(handler)
        return handlers
    except Exception as e:
        logger.error(f"Fehler beim Lesen der CSV-Datei: {e}")
        raise

def add_handlers_to_database(conn, handlers: Set[str]) -> None:
    """Fügt die Handler zur Datenbank hinzu."""
    try:
        with conn.cursor() as cursor:
            # Hole existierende Handler
            cursor.execute("SELECT Initials, Name FROM Handlers;")
            existing_handlers = {row['Name']: row['Initials'] for row in cursor.fetchall()}
            
            # Füge neue Handler hinzu
            for handler in handlers:
                if handler not in existing_handlers:
                    # Generiere Initials aus dem Namen (erste Buchstaben der Wörter)
                    initials = ''.join(word[0].upper() for word in handler.split() if word)
                    if len(initials) > 3:  # Begrenze auf 3 Zeichen
                        initials = initials[:3]
                    
                    # Stelle sicher, dass die Initials einzigartig sind
                    base_initials = initials
                    counter = 1
                    while initials in existing_handlers.values():
                        initials = f"{base_initials}{counter}"
                        counter += 1
                    
                    try:
                        cursor.execute(
                            "INSERT INTO Handlers (Initials, Name) VALUES (%s, %s);",
                            (initials, handler)
                        )
                        logger.info(f"Handler hinzugefügt: {handler} ({initials})")
                        existing_handlers[handler] = initials
                    except Exception as e:
                        logger.error(f"Fehler beim Hinzufügen des Handlers {handler}: {e}")
                        continue
            
            conn.commit()
            logger.info("Handler-Import abgeschlossen")
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Handler: {e}")
        raise

def main() -> None:
    try:
        password = input("Bitte KeePass Master-Passwort eingeben: ")
        keepass_handler = KeepassHandler(password)
        db_connection = DatabaseConnection(keepass_handler)
        csv_path = Path(__file__).parent / "RMA Geräte Retourerfassung - ILI B2C.csv"
        
        with db_connection.get_connection() as conn:
            # Extrahiere Handler aus CSV
            handlers = extract_handlers_from_csv(csv_path)
            logger.info(f"Gefundene Handler in CSV: {', '.join(sorted(handlers))}")
            
            # Füge Handler zur Datenbank hinzu
            add_handlers_to_database(conn, handlers)
            
    except DatabaseConnectionError as e:
        logger.error(f"Fehler beim Ausführen des Skripts: {e}")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")

if __name__ == "__main__":
    main() 