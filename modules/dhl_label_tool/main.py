import os
import sys
import traceback
import logging
from shared.credentials.credential_cache import get_credential_cache
from shared.credentials.keepass_handler import CentralKeePassHandler
from modules.dhl_label_tool.label_generator import DHLLabelGenerator
from modules.dhl_label_tool.login_window import LoginWindow
import modules.dhl_label_tool.resources as resources
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFile
from shared.utils.enhanced_logging import (
    LoggingMessageBox, 
    log_error_and_show_dialog, 
    get_module_logger
)
from shared.utils.logger import LogBlock

# Optional: Importiere das LoginWindow für den Notfall-Login

def show_error_message(message):
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setWindowTitle("Fehler")
    error_dialog.setText(message)
    error_dialog.exec()

def get_database_path():
    # Verwende die zentrale KeePass-Datenbank
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, "credentials.kdbx")

def get_style_path():
    # Verwende das globale I LOCK IT Stylesheet
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, "global_style.qss")

def start_dhl_label_tool_widget(kp_handler: CentralKeePassHandler):
    """Startet das DHL Label Tool als Widget mit bereits geöffnetem KeePass-Handler."""
    try:
        logger = get_module_logger("DHL-Label-Tool")
        
        with LogBlock(logger, logging.INFO) as log:
            try:
                log.section("DHL API")
                # DHL API Zugangsdaten
                dhl_api_username, dhl_api_password = kp_handler.get_credentials("DHL API Zugangsdaten", group="DHL Label Tool")
                log("DHL API Zugangsdaten geladen")
                if not all([dhl_api_username, dhl_api_password]):
                    show_error_message("Fehler: DHL API Zugangsdaten (Username/Password) konnten nicht geladen werden.")
                    return None
            except Exception as e:
                logger.error(f"Fehler beim Laden der DHL API Zugangsdaten: {str(e)}")
                show_error_message(f"Fehler beim Laden der DHL API Zugangsdaten: {str(e)}")
                return None

            try:
                log.section("DHL Client")
                # DHL Client Credentials
                client_id, client_secret = kp_handler.get_credentials("DHL Client Credentials", group="DHL Label Tool")
                log("DHL Client Credentials geladen")
                if not all([client_id, client_secret]):
                    show_error_message("Fehler: DHL Client Credentials (ID/Secret) konnten nicht geladen werden.")
                    return None
            except Exception as e:
                logger.error(f"Fehler beim Laden der DHL Client Credentials: {str(e)}")
                show_error_message(f"Fehler beim Laden der DHL Client Credentials: {str(e)}")
                return None

            try:
                log.section("Zendesk")
                # Zendesk API Token
                zendesk_email, zendesk_token = kp_handler.get_credentials("Zendesk API Token", group="shared")
                log("Zendesk API Zugangsdaten geladen")
                if not all([zendesk_email, zendesk_token]):
                    show_error_message("Fehler: Zendesk API Zugangsdaten (Email/Token) konnten nicht geladen werden.")
                    return None
            except Exception as e:
                logger.error(f"Fehler beim Laden der Zendesk API Zugangsdaten: {str(e)}")
                show_error_message(f"Fehler beim Laden der Zendesk API Zugangsdaten: {str(e)}")
                return None

            try:
                log.section("Billbee")
                # Billbee API Key
                bb_api_key = kp_handler.get_credentials("BillBee API Key", group="shared")[1]
                log("Billbee API Key geladen")
                if not bb_api_key:
                    show_error_message("Fehler: Billbee API Key konnte nicht geladen werden.")
                    return None

                # Billbee Basic Auth
                bb_auth = kp_handler.get_credentials("BillBee Basic Auth", group="shared")
                bb_api_user = bb_auth[0]
                bb_api_password = bb_auth[1]
                log("Billbee Basic Auth Daten geladen")
                if not all([bb_api_user, bb_api_password]):
                    show_error_message("Fehler: Billbee Basic Auth Daten konnten nicht geladen werden.")
                    return None
            except Exception as e:
                logger.error(f"Fehler beim Laden der Billbee Zugangsdaten: {str(e)}")
                show_error_message(f"Fehler beim Laden der Billbee Zugangsdaten: {str(e)}")
                return None

            try:
                log.section("DHL Billing")
                # DHL Billing
                billing_number = kp_handler.get_credentials("DHL Billing", group="DHL Label Tool")[0]
                log("DHL Billing Number geladen")
                if not billing_number:
                    show_error_message("Fehler: DHL Billing Number konnte nicht geladen werden.")
                    return None
            except Exception as e:
                logger.error(f"Fehler beim Laden der DHL Billing Number: {str(e)}")
                show_error_message(f"Fehler beim Laden der DHL Billing Number: {str(e)}")
                return None

        with LogBlock(logger, logging.INFO) as log:
            main_window = DHLLabelGenerator()
            main_window.setWindowIcon(QIcon(":/icons/icon.ico"))
            
            # Setze die geladenen Credentials direkt
            main_window.username = dhl_api_username
            main_window.password = dhl_api_password
            main_window.client_id = client_id
            main_window.client_secret = client_secret
            main_window.zendesk_email = zendesk_email
            main_window.zendesk_token = zendesk_token
            main_window.bb_api_key = bb_api_key
            main_window.bb_api_user = bb_api_user
            main_window.bb_api_password = bb_api_password
            main_window.billing_number = billing_number
            
            log("Hauptfenster wird angezeigt")
            main_window.show()
            return main_window
            
    except Exception as e:
        logger.error(f"Fehler beim Starten der Anwendung: {str(e)}")
        show_error_message(f"Fehler beim Starten der Anwendung: {str(e)}")
        return None

def main():
    try:
        logger = get_module_logger("DHL-Label-Tool")
        logger.info("Anwendung wird gestartet")

        # Verwende die bestehende QApplication statt eine neue zu erstellen
        app = QApplication.instance()
        if app is None:
            # Fallback: Erstelle eine neue QApplication nur wenn keine existiert
            app = QApplication(sys.argv)
        
        app.setWindowIcon(QIcon(":/icons/icon.ico"))
        
        # Lade Stylesheet
        stylesheet_path = ":/global_style.qss"
        qss_file = QFile(stylesheet_path)
        if qss_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stylesheet = str(qss_file.readAll(), encoding="utf-8")
            app.setStyleSheet(stylesheet)
        else:
            logger.error("Das Stylesheet konnte nicht geladen werden.")

        # Versuche zentralen Handler aus dem CredentialCache zu holen
        credential_cache = get_credential_cache()
        kp_handler = credential_cache.get_keepass_handler()
        if not kp_handler or not kp_handler.is_database_open():
            # Kein zentraler Login vorhanden, zeige Login-Fenster
            logger.info("Kein zentraler Login gefunden, zeige Login-Fenster")
            database_path = get_database_path()
            kp_handler = CentralKeePassHandler(database_path)
            login_window = LoginWindow(kp_handler)
            if login_window.exec() != QDialog.DialogCode.Accepted:
                return None  # Kein sys.exit(), nur return None
            # Nach erfolgreichem Login im Cache speichern
            credential_cache.set_keepass_handler(kp_handler)
        else:
            logger.info("Zentraler Login gefunden, nutze zentralen Handler")

        # Starte das Hauptfenster mit zentralem Handler
        with LogBlock(logger, logging.INFO) as log:
            main_window = DHLLabelGenerator()
            main_window.setWindowIcon(QIcon(":/icons/icon.ico"))

            # Credentials laden
            log.section("DHL API")
            # DHL API Zugangsdaten
            dhl_api_username, dhl_api_password = kp_handler.get_credentials("DHL API Zugangsdaten", group="DHL Label Tool")
            log("DHL API Zugangsdaten geladen")
            main_window.username = dhl_api_username
            main_window.password = dhl_api_password

            log.section("DHL Client")
            # DHL Client Credentials
            client_id, client_secret = kp_handler.get_credentials("DHL Client Credentials", group="DHL Label Tool")
            log("DHL Client Credentials geladen")
            main_window.client_id = client_id
            main_window.client_secret = client_secret

            log.section("Zendesk")
            # Zendesk API Token
            zendesk_email, zendesk_token = kp_handler.get_credentials("Zendesk API Token", group="shared")
            log("Zendesk API Zugangsdaten geladen")
            main_window.zendesk_email = zendesk_email
            main_window.zendesk_token = zendesk_token

            log.section("Billbee")
            # Billbee API Key
            bb_api_key = kp_handler.get_credentials("BillBee API Key", group="shared")[1]
            # Billbee Basic Auth
            bb_auth = kp_handler.get_credentials("BillBee Basic Auth", group="shared")
            bb_api_user = bb_auth[0]
            bb_api_password = bb_auth[1]
            log("Billbee Zugangsdaten geladen")
            main_window.bb_api_key = bb_api_key
            main_window.bb_api_user = bb_api_user
            main_window.bb_api_password = bb_api_password

            log.section("DHL Billing")
            # DHL Billing
            billing_number = kp_handler.get_credentials("DHL Billing", group="DHL Label Tool")[0]
            main_window.billing_number = billing_number
            log("DHL Billing Number geladen")

            log("Hauptfenster wird angezeigt")
            main_window.show()
            return main_window  # Kein sys.exit(), nur return main_window

    except Exception as e:
        logger = get_module_logger("DHL-Label-Tool")
        logger.error(f"Fehler beim Starten der Anwendung: {str(e)}")
        show_error_message(f"Fehler beim Starten der Anwendung: {str(e)}")
        traceback.print_exc()
        return None  # Kein sys.exit(), nur return None

def start_dhl_label_tool():
    """Startet das DHL Label Tool direkt mit lokalen Modulen."""
    try:
        # Füge das aktuelle Verzeichnis zum Python-Pfad hinzu
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        # Führe die neue main-Funktion aus (ohne sys.exit())
        return main()
    except Exception as e:
        print(f"Fehler beim Starten des DHL Label Tools: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Erstelle eine QApplication wenn das Modul direkt ausgeführt wird
    app = QApplication(sys.argv)
    main()
    sys.exit(app.exec())