import os
import sys
import traceback
from keepass import KeePassHandler
from label_generator import DHLLabelGenerator
from login_window import LoginWindow
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QFile
from utils import setup_logger, LogBlock
import logging
import resources


def show_error_message(message):
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Critical)
    error_dialog.setWindowTitle("Fehler")
    error_dialog.setText(message)
    error_dialog.exec_()

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

def get_style_path():
    if getattr(sys, "frozen", False):
        # Wenn die Anwendung als ausführbare Datei läuft
        base_path = os.path.dirname(sys.executable)
        internal_path = os.path.join(base_path, "_internal")
        return os.path.join(internal_path, "global_style.qss")
    else:
        # Wenn die Anwendung im Entwicklungsmodus läuft
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, "global_style.qss")

def main():
    try:
        logger = setup_logger()
        
        with LogBlock(logger, "Initialisierung") as log:
            # Verwende die bereits definierte Funktion zur Pfadermittlung
            database_path = get_database_path()
            log("Datenbank-Pfad: " + database_path)

            kp_handler = KeePassHandler(database_path)
            app = QApplication(sys.argv)
            app.setWindowIcon(QIcon(":/icons/icon.ico"))

            # Lade das Stylesheet
            style_path = get_style_path()
            log.section("Stylesheet")
            log("Stylesheet-Pfad: " + style_path)
            
            if os.path.exists(style_path):
                with open(style_path, "r", encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
                    log("Stylesheet erfolgreich geladen")
            else:
                logger.error("Stylesheet nicht gefunden: " + style_path)

            log.section("KeePass")
            log("Initialisiere KeePass Handler")
            
            login_window = LoginWindow(kp_handler)
            if login_window.exec_() != QDialog.Accepted:
                sys.exit(0)

        with LogBlock(logger, "API Zugangsdaten") as log:
            try:
                log.section("DHL API")
                dhl_api_username, dhl_api_password = kp_handler.get_credentials("DHL API Zugangsdaten")
                log("DHL API Zugangsdaten geladen")
                if not all([dhl_api_username, dhl_api_password]):
                    show_error_message("Fehler: DHL API Zugangsdaten (Username/Password) konnten nicht geladen werden.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Fehler beim Laden der DHL API Zugangsdaten: {str(e)}")
                show_error_message(f"Fehler beim Laden der DHL API Zugangsdaten: {str(e)}")
                sys.exit(1)

            try:
                log.section("DHL Client")
                client_id, client_secret = kp_handler.get_credentials("DHL Client Credentials")
                log("DHL Client Credentials geladen")
                if not all([client_id, client_secret]):
                    show_error_message("Fehler: DHL Client Credentials (ID/Secret) konnten nicht geladen werden.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Fehler beim Laden der DHL Client Credentials: {str(e)}")
                show_error_message(f"Fehler beim Laden der DHL Client Credentials: {str(e)}")
                sys.exit(1)

            try:
                log.section("Zendesk")
                zendesk_email, zendesk_token = kp_handler.get_credentials("Zendesk API Token")
                log("Zendesk API Zugangsdaten geladen")
                if not all([zendesk_email, zendesk_token]):
                    show_error_message("Fehler: Zendesk API Zugangsdaten (Email/Token) konnten nicht geladen werden.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Zendesk API Zugangsdaten: {str(e)}")
                show_error_message(f"Fehler beim Laden der Zendesk API Zugangsdaten: {str(e)}")
                sys.exit(1)

            try:
                log.section("Billbee")
                bb_api_key = kp_handler.get_credentials("BillBee API Key")[1]
                log("Billbee API Key geladen")
                if not bb_api_key:
                    show_error_message("Fehler: Billbee API Key konnte nicht geladen werden.")
                    sys.exit(1)

                bb_auth = kp_handler.get_credentials("BillBee Basic Auth")
                bb_api_user = bb_auth[0]
                bb_api_password = bb_auth[1]
                log("Billbee Basic Auth Daten geladen")
                if not all([bb_api_user, bb_api_password]):
                    show_error_message("Fehler: Billbee Basic Auth Daten konnten nicht geladen werden.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Billbee Zugangsdaten: {str(e)}")
                show_error_message(f"Fehler beim Laden der Billbee Zugangsdaten: {str(e)}")
                sys.exit(1)

            try:
                log.section("DHL Billing")
                billing_number = kp_handler.get_credentials("DHL Billing")[0]
                log("DHL Billing Number geladen")
                if not billing_number:
                    show_error_message("Fehler: DHL Billing Number konnte nicht geladen werden.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Fehler beim Laden der DHL Billing Number: {str(e)}")
                show_error_message(f"Fehler beim Laden der DHL Billing Number: {str(e)}")
                sys.exit(1)

        with LogBlock(logger, "Anwendungsstart") as log:
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
            sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Fehler beim Starten der Anwendung: {str(e)}")
        show_error_message(f"Fehler beim Starten der Anwendung: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()