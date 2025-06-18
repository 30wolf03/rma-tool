from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError, HeaderChecksumError
import os
from utils import setup_logger, LogBlock

class KeePassHandler:
    def __init__(self, database_path):
        """
        Initialisiert den KeePassHandler mit dem Pfad zur KeePass-Datenbank.
        """
        self.logger = setup_logger()
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
            return entry.username, entry.password
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Zugangsdaten: {str(e)}")
            return None, None
