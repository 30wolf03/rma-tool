"""Handler für die Validierung von Benutzer-Initialen.

Dieses Modul stellt Funktionen zur Validierung und Überprüfung von
Benutzer-Initialen bereit, die für die RMA-Datenbank verwendet werden.
"""

from __future__ import annotations

from typing import Optional, Tuple, Dict
import re

from loguru import logger

from ..database.connection import DatabaseConnection, DatabaseConnectionError


class HandlerValidationError(Exception):
    """Basis-Exception für Handler-Validierungsfehler."""
    pass


class InvalidInitialsError(HandlerValidationError):
    """Exception für ungültige Initialen."""
    pass


class HandlerNotFoundError(HandlerValidationError):
    """Exception wenn ein Handler nicht in der Datenbank gefunden wurde."""
    pass


def validate_initials_format(initials: str) -> str:
    """Validiert das Format der Initialen.
    
    Args:
        initials: Die zu validierenden Initialen
        
    Returns:
        str: Die validierten Initialen in Großbuchstaben
        
    Raises:
        InvalidInitialsError: Wenn die Initialen ungültig sind
    """
    if not initials:
        raise InvalidInitialsError("Initialen dürfen nicht leer sein")
        
    # Entferne Leerzeichen und konvertiere zu Großbuchstaben
    initials = initials.strip().upper()
    
    # Prüfe Format (1-5 Großbuchstaben)
    if not re.match(r'^[A-Z]{1,5}$', initials):
        raise InvalidInitialsError(
            "Initialen müssen aus 1-5 Großbuchstaben bestehen"
        )
        
    return initials


def validate_handler_exists(
    db_connection: DatabaseConnection,
    initials: str
) -> Tuple[str, str]:
    """Überprüft, ob ein Handler mit den gegebenen Initialen existiert.
    
    Args:
        db_connection: Die Datenbankverbindung
        initials: Die zu überprüfenden Initialen
        
    Returns:
        Tuple[str, str]: (Initials, Name) des Handlers
        
    Raises:
        HandlerNotFoundError: Wenn der Handler nicht gefunden wurde
        InvalidInitialsError: Wenn die Initialen ungültig sind
    """
    try:
        # Validiere Format
        initials = validate_initials_format(initials)
        
        # Suche Handler in der Datenbank
        results = db_connection.execute_query("""
            SELECT Initials, Name 
            FROM Handlers 
            WHERE Initials = %s
        """, (initials,))
        
        if not results:
            raise HandlerNotFoundError(
                f"Handler mit Initialen '{initials}' nicht gefunden"
            )
            
        handler = results[0]
        return handler['Initials'], handler['Name']
        
    except DatabaseConnectionError as e:
        logger.error(f"Datenbankfehler bei Handler-Validierung: {e}")
        raise HandlerValidationError(f"Datenbankfehler: {e}") from e


def get_all_handlers(db_connection: DatabaseConnection) -> Dict[str, str]:
    """Gibt alle verfügbaren Handler zurück.
    
    Args:
        db_connection: Die Datenbankverbindung
        
    Returns:
        Dict[str, str]: Dictionary mit Initials als Schlüssel und Name als Wert
        
    Raises:
        HandlerValidationError: Bei Datenbankfehlern
    """
    try:
        results = db_connection.execute_query("""
            SELECT Initials, Name 
            FROM Handlers 
            ORDER BY Initials
        """)
        
        return {row['Initials']: row['Name'] for row in results}
        
    except DatabaseConnectionError as e:
        logger.error(f"Datenbankfehler beim Abrufen der Handler: {e}")
        raise HandlerValidationError(f"Datenbankfehler: {e}") from e 