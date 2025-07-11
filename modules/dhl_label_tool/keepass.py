from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError, HeaderChecksumError
import os
import sys
import logging
import re
import traceback
from io import StringIO
from datetime import datetime
from shared.utils.logger import setup_logger, LogBlock

def mask_password(password: str, visible_chars: int = 5) -> str:
    """
    Kürzt ein Passwort für das Logging, sodass nur die ersten n Zeichen sichtbar sind.
    
    Args:
        password: Das zu maskierende Passwort
        visible_chars: Anzahl der sichtbaren Zeichen am Anfang (Standard: 5)
        
    Returns:
        Das maskierte Passwort im Format "XXXXX..." oder "XXXXX" wenn das Passwort kürzer ist
    """
    if not password:
        return ""
    
    if len(password) <= visible_chars:
        return "X" * len(password)
        
    return password[:visible_chars] + "..."


class KeePassHandler:
    def __init__(self, database_path):
        """
        Initialisiert den KeePassHandler mit dem Pfad zur KeePass-Datenbank.
        """
        self.logger = setup_logger("RMA-Tool.Shared-Infrastructure.KeePass")
        self.database_path = database_path
        self.kp = None
        self.logger.info(f"KeePassHandler initialisiert mit Datenbank: {database_path}")

    def open_database(self, password):
        """Öffnet die KeePass-Datenbank mit dem Master-Passwort."""
        try:
            self.logger.info(f"-" * 80)
            self.logger.info(f"Versuche Datenbank zu öffnen: {self.database_path}")
            self.logger.debug(f"Datei existiert: {os.path.exists(self.database_path)}")
            self.logger.debug(f"Dateigröße: {os.path.getsize(self.database_path)} bytes")
            self.logger.debug(f"Verwende Master-Passwort: {mask_password(password)}")

            self.kp = PyKeePass(self.database_path, password=password)
            self.logger.info("Datenbank erfolgreich geöffnet.")
            self.logger.info(f"-" * 80)
            return True
            
        except Exception as e:
            self.logger.error(f"-" * 80)
            self.logger.error(f"Fehlertyp: {type(e).__name__}")
            self.logger.error(f"Fehlermeldung: {str(e)}")
            self.logger.error(f"-" * 80)
            return False
        
        

    def get_credentials(self, entry_title):
        """
        Ruft die Zugangsdaten (Benutzername und Passwort) für einen bestimmten Eintrag ab.
        """
        if not self.kp:
            self.logger.error("Die Datenbank ist nicht geöffnet.")
            return None, None

        try:
            entry = self.kp.find_entries(title=entry_title, first=True)
            if not entry:
                self.logger.error(f"Eintrag '{entry_title}' nicht gefunden!")
                return None, None

            self.logger.info(f"Eintrag '{entry_title}' gefunden.")
            if entry.password:
                self.logger.debug(f"Passwort für '{entry_title}': {mask_password(entry.password)}")
            return entry.username, entry.password
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Zugangsdaten: {str(e)}")
            return None, None

def get_database_path():
    if getattr(sys, "frozen", False):
        # Wenn die Anwendung als ausführbare Datei läuft
        base_path = os.path.dirname(sys.executable)
        internal_path = os.path.join(base_path, "_internal")
        return os.path.join(internal_path, "DHL_Label_Generator_secrets.kdbx")
    else:
        # Wenn die Anwendung im Entwicklungsmodus läuft
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, "DHL_Label_Generator_secrets.kdbx")

def load_credentials(master_password):
    """Lädt alle API-Credentials aus der KeePass-Datenbank."""
    try:
        # Pfad zur KeePass-Datei
        database_path = get_database_path()
        
        # Erstelle eine Instanz des KeePassHandlers
        kp_handler = KeePassHandler(database_path)
        
        # Öffne die Datenbank mit dem übergebenen Master-Passwort
        if not kp_handler.open_database(master_password):
            raise Exception("Konnte die KeePass-Datenbank nicht öffnen")
        
        # Lade die Credentials für verschiedene Dienste
        credentials = {}
        
        # DHL Credentials
        dhl_username, dhl_password = kp_handler.get_credentials("DHL API Zugangsdaten")
        if dhl_username and dhl_password:
            credentials['dhl_username'] = dhl_username
            credentials['dhl_password'] = dhl_password
        
        # DHL Client Credentials
        dhl_client_id, dhl_client_secret = kp_handler.get_credentials("DHL Client Credentials")
        if dhl_client_id and dhl_client_secret:
            credentials['dhl_client_id'] = dhl_client_id
            credentials['dhl_client_secret'] = dhl_client_secret
        
        # DHL Billing Number
        dhl_billing, _ = kp_handler.get_credentials("DHL Billing")
        if dhl_billing:
            credentials['dhl_billing_number'] = dhl_billing
        
        # Zendesk Credentials
        zendesk_email, zendesk_token = kp_handler.get_credentials("Zendesk API Token")
        if zendesk_email and zendesk_token:
            credentials['zendesk_email'] = zendesk_email
            credentials['zendesk_token'] = zendesk_token
        
        # Billbee Credentials
        billbee_api_key, billbee_api_user = kp_handler.get_credentials("BillBee API Key")
        if billbee_api_key and billbee_api_user:
            credentials['billbee_api_key'] = billbee_api_key
            credentials['billbee_api_user'] = billbee_api_user
        
        billbee_password, _ = kp_handler.get_credentials("BillBee Basic Auth")
        if billbee_password:
            credentials['billbee_api_password'] = billbee_password
        
        return credentials
        
    except Exception as e:
        raise Exception(f"Fehler beim Laden der Credentials: {str(e)}")
