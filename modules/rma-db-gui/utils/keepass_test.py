"""Test-Skript für die KeePass-Integration."""

from pathlib import Path
import sys
from typing import List

from loguru import logger

# Füge das übergeordnete Verzeichnis zum Python-Pfad hinzu
sys.path.append(str(Path(__file__).resolve().parent.parent))

from .keepass_handler import KeepassHandler
from ..config.settings import SSH_ENTRY, MYSQL_ENTRY

def test_keepass_entries(password: str) -> None:
    """Testet die KeePass-Einträge und gibt Informationen aus.
    
    Args:
        password: Das KeePass-Master-Passwort
    """
    try:
        handler = KeepassHandler(password)
        
        # Teste SSH-Eintrag
        logger.info("Teste SSH-Eintrag...")
        ssh_creds = handler.get_ssh_credentials()
        logger.info(f"SSH-Eintrag gefunden:")
        logger.info(f"  Username: {ssh_creds['username']}")
        logger.info(f"  URL: {ssh_creds['url']}")
        logger.info(f"  Private Key vorhanden: {'Ja' if ssh_creds['private_key'] else 'Nein'}")
        
        # Teste MySQL-Eintrag
        logger.info("\nTeste MySQL-Eintrag...")
        mysql_creds = handler.get_mysql_credentials()
        logger.info(f"MySQL-Eintrag gefunden:")
        logger.info(f"  Username: {mysql_creds['username']}")
        logger.info(f"  Host: {mysql_creds['host']}")
        
    except Exception as e:
        logger.error(f"Fehler beim Testen der KeePass-Einträge: {e}")
        raise

if __name__ == "__main__":
    password = input("Bitte KeePass Master-Passwort eingeben: ")
    test_keepass_entries(password) 