"""Skript zum Importieren der CSV-Daten in die RMA-Datenbank (angepasst an die echte Struktur)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging
import sys
import re

from loguru import logger

from ..database.connection import DatabaseConnection, DatabaseConnectionError
from ..utils.keepass_handler import KeepassHandler

# Konfiguriere das Logging (z. B. auf DEBUG-Level, damit auch Warnungen ausgegeben werden)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

# Füge das übergeordnete Verzeichnis zum Python-Pfad hinzu, damit die Module gefunden werden
sys.path.append(str(Path(__file__).resolve().parent.parent))

def parse_date(date_str: str) -> Optional[str]:
    """Konvertiert einen Datumsstring in ein SQL-kompatibles Format (YYYY-MM-DD)."""
    if not date_str or date_str.strip() in ('', '-'):  # '-' als Platzhalter ignorieren
        return None
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        logger.warning(f"Ungültiges Datum: {date_str}")
        return None

def translate_last_action(action: str) -> str:
    """Übersetzt die letzte Aktion aus dem Deutschen ins Englische."""
    if not action or action.strip() == '':
        return None  # Leere Werte werden als NULL gespeichert
        
    action = action.strip().lower()
    translations = {
        'eingang erfasst': 'Entry recorded',
        'reparatur': 'Repair',
        'nicht reparabel': 'Not repairable',
        'rückzahlung': 'Refund',
        'austausch': 'Exchange',
        'widerruf': 'Cancelled'
    }
    translated = translations.get(action)
    if translated is None:
        logger.warning(f"Unbekannte Aktion '{action}' wird als NULL gespeichert")
        return None
    return translated

def determine_status(row: Dict[str, str]) -> str:
    """Bestimmt den Status: Completed, wenn Ausgangsdatum oder letzte Aktion 'Refund', sonst Open."""
    has_exit_date = bool(row['Ausgang'] and row['Ausgang'].strip() and row['Ausgang'].strip() != '-')
    is_refund = translate_last_action(row['letzte Aktion']) == 'Refund'
    return 'Completed' if (has_exit_date or is_refund) else 'Open'

def get_ordernumber(row: Dict[str, str]) -> str:
    """Gibt die OrderNumber zurück (Amazon Bestellnr. oder leere Zeichenkette)."""
    return row.get('Amazon Bestellnr.', '').strip() or ''

def generate_ticket_number(amazon_order_number):
    if amazon_order_number and not amazon_order_number.strip() == "":
        return "AMZ" + amazon_order_number.strip()
    return None

def analyze_storage_locations_table(conn) -> None:
    """Analysiert die Struktur der StorageLocations-Tabelle und gibt die Spalteninformationen aus."""
    try:
        with conn.cursor() as cursor:
            # Hole Spalteninformationen
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'StorageLocations'
                ORDER BY ORDINAL_POSITION;
            """)
            columns = cursor.fetchall()
            logger.info("StorageLocations Tabellenstruktur:")
            for col in columns:
                logger.info(f"  Spalte: {col['COLUMN_NAME']}, Typ: {col['DATA_TYPE']}, "
                          f"Schlüssel: {col['COLUMN_KEY']}, Nullable: {col['IS_NULLABLE']}")
            
            # Hole Beispieldaten
            cursor.execute("SELECT * FROM StorageLocations LIMIT 5;")
            sample_data = cursor.fetchall()
            logger.info("\nBeispieldaten aus StorageLocations:")
            for row in sample_data:
                logger.info(f"  {row}")
    except Exception as e:
        logger.error(f"Fehler bei der Analyse der StorageLocations-Tabelle: {e}")
        raise

def get_storage_location_id(conn, storage_location_name: str) -> Optional[int]:
    """Gibt die ID des Lagerorts zurück, basierend auf dem Namen.
    
    Args:
        conn: Datenbankverbindung
        storage_location_name: Name des Lagerorts
        
    Returns:
        Optional[int]: ID des Lagerorts oder None, wenn nicht gefunden
    """
    if not storage_location_name or storage_location_name.strip() == "":
        return None
        
    try:
        with conn.cursor() as cursor:
            # Versuche verschiedene mögliche Spaltennamen
            possible_columns = ['LocationName', 'Name', 'StorageName', 'Location']
            
            for column in possible_columns:
                try:
                    cursor.execute(f"SELECT ID FROM StorageLocations WHERE {column} = %s;", 
                                 (storage_location_name.strip(),))
                    row = cursor.fetchone()
                    if row:
                        logger.debug(f"Lagerort '{storage_location_name}' gefunden in Spalte {column}")
                        return row['ID']
                except pymysql.MySQLError as e:
                    logger.debug(f"Spalte {column} nicht gefunden: {e}")
                    continue
                    
            logger.warning(f"Lagerort '{storage_location_name}' in keiner Spalte gefunden")
            return None
    except Exception as e:
        logger.error(f"Fehler beim Abfragen des Lagerorts {storage_location_name}: {e}")
        return None

def analyze_handlers_table(conn) -> None:
    """Analysiert die Struktur der Handlers-Tabelle und gibt die Handler-Informationen aus."""
    try:
        with conn.cursor() as cursor:
            # Hole Spalteninformationen
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'Handlers'
                ORDER BY ORDINAL_POSITION;
            """)
            columns = cursor.fetchall()
            logger.info("Handlers Tabellenstruktur:")
            for col in columns:
                logger.info(f"  Spalte: {col['COLUMN_NAME']}, Typ: {col['DATA_TYPE']}, "
                          f"Schlüssel: {col['COLUMN_KEY']}, Nullable: {col['IS_NULLABLE']}")
            
            # Hole alle Handler
            cursor.execute("SELECT * FROM Handlers ORDER BY Initials;")
            handlers = cursor.fetchall()
            logger.info("\nVerfügbare Handler:")
            for handler in handlers:
                logger.info(f"  Initials: {handler['Initials']}, Name: {handler.get('Name', 'N/A')}")
            
            return handlers
    except Exception as e:
        logger.error(f"Fehler bei der Analyse der Handlers-Tabelle: {e}")
        raise

def get_handler_initials(conn, handler_name: str, available_handlers: list) -> Optional[str]:
    """Gibt die Initials des Handlers zurück.
    
    Args:
        conn: Datenbankverbindung
        handler_name: Name oder Initials des Handlers
        available_handlers: Liste der verfügbaren Handler
        
    Returns:
        Optional[str]: Initials des Handlers oder None, wenn nicht gefunden
    """
    if not handler_name or handler_name.strip() == "":
        return None
        
    handler_name = handler_name.strip().strip("'")  # Entferne Anführungszeichen
    
    # Prüfe zuerst, ob es sich um Initials handelt
    for handler in available_handlers:
        if handler['Initials'] == handler_name:
            return handler_name
    
    # Wenn keine Übereinstimmung gefunden wurde, suche nach dem Namen
    for handler in available_handlers:
        if handler['Name'] == handler_name:
            return handler['Initials']
    
    logger.warning(f"Handler '{handler_name}' nicht in der Datenbank gefunden")
    return None

def import_csv_data(csv_path: Path, conn) -> None:
    """Importiert die CSV-Daten in die Datenbank."""
    try:
        # Hole verfügbare Handler
        available_handlers = analyze_handlers_table(conn)
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            cursor = conn.cursor()
            cursor.execute("START TRANSACTION")
            try:
                for row in reader:
                    ticket = row['Ticketnr.'].strip()
                    order = get_ordernumber(row)
                    handler_initials = get_handler_initials(conn, row['letzter Bearbeiter'].strip(), available_handlers)
                    
                    # RMA_Cases
                    cursor.execute(
                        """
                        INSERT INTO RMA_Cases (
                            TicketNumber, OrderNumber, Type, EntryDate, Status, ExitDate, TrackingNumber, IsAmazon, StorageLocationID
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE EntryDate=VALUES(EntryDate), Status=VALUES(Status), ExitDate=VALUES(ExitDate)
                        """,
                        (
                            ticket,
                            order,
                            "Repair",
                            parse_date(row['Eingang']),
                            determine_status(row),
                            parse_date(row['Ausgang']),
                            row.get('Tracking', '').strip(),
                            int(bool(order)),
                            get_storage_location_id(conn, row.get('Lagerort', '').strip())
                        )
                    )
                    # RMA_Products
                    cursor.execute(
                        """
                        INSERT INTO RMA_Products (
                            TicketNumber, OrderNumber, ProductName, SerialNumber, Quantity
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            ticket,
                            order,
                            row['Hauptrodukt'].strip(),
                            row['Seriennumer'].strip(),
                            1
                        )
                    )
                    # RMA_RepairDetails
                    cursor.execute(
                        """
                        INSERT INTO RMA_RepairDetails (
                            TicketNumber, OrderNumber, CustomerDescription, ProblemCause, LastHandler, LastAction
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            ticket,
                            order,
                            row['Problembeschreibung vom Kunden'].strip(),
                            None,
                            handler_initials,  # Verwende die gefundenen Initials
                            translate_last_action(row['letzte Aktion'])
                        )
                    )
                cursor.execute("COMMIT")
                logger.info("CSV-Daten erfolgreich importiert")
            except Exception as e:
                cursor.execute("ROLLBACK")
                logger.error(f"Fehler beim Importieren der CSV-Daten: {e}")
                raise
    except Exception as e:
        logger.error(f"Fehler beim Importieren der CSV-Daten: {e}")
        raise

def test_database_connection_and_storage_locations(conn):
    """Testet die Datenbankverbindung und gibt alle Lagerorte aus."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT ID, LocationName FROM StorageLocations;")
            rows = cursor.fetchall()
            logger.info(f"StorageLocations-Einträge ({len(rows)}):")
            for row in rows:
                logger.info(f"  ID: {row['ID']}, LocationName: {row['LocationName']}")
    except Exception as e:
        logger.error(f"Fehler beim Testen der StorageLocations-Tabelle: {e}")
        raise

def main() -> None:
    try:
        password = input("Bitte KeePass Master-Passwort eingeben: ")
        keepass_handler = KeepassHandler(password)
        db_connection = DatabaseConnection(keepass_handler)
        csv_path = Path(__file__).parent / "RMA Geräte Retourerfassung - ILI B2C.csv"
        with db_connection.get_connection() as conn:
            # Analysiere die Tabellenstruktur
            analyze_storage_locations_table(conn)
            # Teste die Verbindung und die StorageLocations-Tabelle
            test_database_connection_and_storage_locations(conn)
            import_csv_data(csv_path, conn)
    except DatabaseConnectionError as e:
        logger.error(f"Fehler beim Ausführen des Import-Skripts: {e}")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")

if __name__ == "__main__":
    main() 