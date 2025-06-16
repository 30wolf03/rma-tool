"""Skript zum Vergleichen der Handler-Werte aus der CSV mit den Datenbankeinträgen."""

from pathlib import Path
import csv
from typing import Set, Dict
import logging
import sys

from loguru import logger

from ..database.connection import DatabaseConnection, DatabaseConnectionError
from ..utils.keepass_handler import KeepassHandler

# Konfiguriere das Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def get_csv_handlers(csv_path: Path) -> Dict[str, int]:
    """Extrahiert alle Handler aus der CSV-Datei mit ihrer Häufigkeit."""
    handlers = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                handler = row.get('letzter Bearbeiter', '').strip()
                if handler and handler != '-':
                    handlers[handler] = handlers.get(handler, 0) + 1
        return handlers
    except Exception as e:
        logger.error(f"Fehler beim Lesen der CSV-Datei: {e}")
        raise

def get_db_handlers(conn) -> Dict[str, str]:
    """Holt alle Handler aus der Datenbank."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT Initials, Name FROM Handlers;")
            return {row['Name']: row['Initials'] for row in cursor.fetchall()}
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Handler aus der Datenbank: {e}")
        raise

def compare_handlers(csv_handlers: Dict[str, int], db_handlers: Dict[str, str]) -> None:
    """Vergleicht die Handler aus CSV und Datenbank."""
    logger.info("\nHandler-Vergleich:")
    logger.info("\nHandler in CSV (nicht in DB):")
    for handler, count in sorted(csv_handlers.items()):
        if handler not in db_handlers:
            logger.info(f"  {handler} (Häufigkeit: {count})")
    
    logger.info("\nHandler in DB:")
    for name, initials in sorted(db_handlers.items()):
        logger.info(f"  Name: {name}, Initials: {initials}")
    
    logger.info("\nHandler in CSV und DB:")
    for handler, count in sorted(csv_handlers.items()):
        if handler in db_handlers:
            logger.info(f"  {handler} -> {db_handlers[handler]} (Häufigkeit: {count})")

def main() -> None:
    try:
        password = input("Bitte KeePass Master-Passwort eingeben: ")
        keepass_handler = KeepassHandler(password)
        db_connection = DatabaseConnection(keepass_handler)
        csv_path = Path(__file__).parent / "RMA Geräte Retourerfassung - ILI B2C.csv"
        
        with db_connection.get_connection() as conn:
            # Hole Handler aus beiden Quellen
            csv_handlers = get_csv_handlers(csv_path)
            db_handlers = get_db_handlers(conn)
            
            # Vergleiche die Handler
            compare_handlers(csv_handlers, db_handlers)
            
    except DatabaseConnectionError as e:
        logger.error(f"Fehler beim Ausführen des Skripts: {e}")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")

if __name__ == "__main__":
    main() 