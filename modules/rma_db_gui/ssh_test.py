"""Testskript für die SSH-Verbindung (mit KeePass-Daten).

Dieses Skript versucht, einen SSH-Tunnel mit den in der KeePass-Datenbank gespeicherten SSH-Credentials aufzubauen und loggt detailliert jeden Schritt.
"""

import sys
import os
import io
import re
from loguru import logger
from sshtunnel import SSHTunnelForwarder

# Füge das Hauptverzeichnis zum Pfad hinzu, damit die Imports funktionieren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.keepass_handler import KeepassHandler, KeepassError

# Konfiguriere das Logging (loguru) so, dass alle Debug-Meldungen angezeigt werden
logger.remove()
logger.add(sys.stderr, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

def test_ssh_connection(master_password: str) -> None:
    """Testet die SSH-Verbindung mit den KeePass-Daten.

    Args:
        master_password (str): Das KeePass-Masterpasswort.
    """
    try:
        logger.info("Starte SSH-Verbindungstest mit KeePass-Daten ...")
        # Erstelle eine Instanz des KeepassHandlers und lade die SSH-Credentials
        kp_handler = KeepassHandler(master_password)
        ssh_creds = kp_handler.get_ssh_credentials()
        logger.info("SSH-Credentials aus KeePass geladen.")

        # Extrahiere Hostname und Port aus der URL (z.B. "testserver.ilockit.bike:345")
        url = ssh_creds["url"]
        match = re.match(r"^(.*?)(?::(\d+))?$", url)
        if not match:
            logger.error(f"Ungültiges URL-Format: {url}")
            return
        hostname = match.group(1)
        port = int(match.group(2)) if match.group(2) else 22
        logger.info(f"Verwende Host: {hostname}, Port: {port}")

        # Prüfe, ob ein privater Schlüssel (traccar.key) vorhanden ist
        private_key = ssh_creds.get("private_key")
        if not private_key:
            logger.error("Kein privater Schlüssel (traccar.key) in den SSH-Credentials gefunden.")
            return
        logger.info("Privater Schlüssel (traccar.key) gefunden.")

        # Erstelle den SSHTunnelForwarder und starte den Tunnel
        tunnel = SSHTunnelForwarder(
            (hostname, port),
            ssh_username=ssh_creds["username"],
            ssh_password=ssh_creds["password"],
            ssh_pkey=io.StringIO(private_key),
            ssh_private_key_password=ssh_creds["password"],
            remote_bind_address=("127.0.0.1", 3306),
            local_bind_address=("127.0.0.1", 0)  # 0 = beliebiger freier Port
        )
        logger.info("SSHTunnelForwarder erstellt. Starte Tunnel ...")
        tunnel.start()
        logger.info("SSH-Tunnel erfolgreich gestartet.")
        tunnel.stop()
        logger.info("SSH-Tunnel gestoppt.")
    except KeepassError as e:
        logger.error(f"KeePass-Fehler: {e}")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim SSH-Test: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
         print("Bitte das KeePass-Masterpasswort als Argument übergeben, z.B.:")
         print("python ssh_test.py <master_password>")
         sys.exit(1)
    master_password = sys.argv[1]
    test_ssh_connection(master_password) 