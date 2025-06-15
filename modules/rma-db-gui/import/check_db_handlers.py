"""Skript zum Überprüfen der Handler-Tabelle in der Datenbank."""

import logging
import sys

from loguru import logger

from ..database.connection import DatabaseConnection, DatabaseConnectionError
from ..utils.keepass_handler import KeepassHandler

# Konfiguriere das Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def main() -> None:
    try:
        password = input("Bitte KeePass Master-Passwort eingeben: ")
        keepass_handler = KeepassHandler(password)
        db_connection = DatabaseConnection(keepass_handler)
        
        with db_connection.get_connection() as conn:
            with conn.cursor() as cursor:
                # Zeige die Tabellenstruktur
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, IS_NULLABLE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'Handlers'
                    ORDER BY ORDINAL_POSITION;
                """)
                columns = cursor.fetchall()
                logger.info("\nHandlers Tabellenstruktur:")
                for col in columns:
                    logger.info(f"  Spalte: {col['COLUMN_NAME']}, Typ: {col['DATA_TYPE']}, "
                              f"Schlüssel: {col['COLUMN_KEY']}, Nullable: {col['IS_NULLABLE']}")
                
                # Zeige alle Handler
                cursor.execute("SELECT * FROM Handlers ORDER BY Initials;")
                handlers = cursor.fetchall()
                logger.info("\nVerfügbare Handler in der Datenbank:")
                for handler in handlers:
                    logger.info(f"  Initials: '{handler['Initials']}', Name: '{handler.get('Name', 'N/A')}'")
                
    except DatabaseConnectionError as e:
        logger.error(f"Fehler beim Ausführen des Skripts: {e}")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")

if __name__ == "__main__":
    main() 