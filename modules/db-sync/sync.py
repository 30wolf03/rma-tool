import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime
from models import Base, Customer, Product, RepairCenter, RMARequest
from config import (
    GOOGLE_SHEETS_SCOPES,
    GOOGLE_SHEETS_SPREADSHEET_ID,
    GOOGLE_SHEETS_RANGE,
    DATABASE_URL,
    KEEPASS_PASSWORD,
    get_ssh_credentials
)
import getpass
import sshtunnel
from sshtunnel import SSHTunnelForwarder

def get_keepass_password():
    """Fragt das KeePass-Passwort zur Laufzeit ab."""
    return getpass.getpass("Bitte geben Sie das KeePass-Passwort ein: ")

def get_google_sheets_service():
    """Stellt die Verbindung zu Google Sheets her."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', GOOGLE_SHEETS_SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', GOOGLE_SHEETS_SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('sheets', 'v4', credentials=creds)

def get_sheet_data(service):
    """Liest Daten aus dem Google Sheet."""
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=GOOGLE_SHEETS_SPREADSHEET_ID,
        range=GOOGLE_SHEETS_RANGE
    ).execute()
    return result.get('values', [])

def setup_database():
    """Stellt die Verbindung zur Datenbank her und erstellt die Tabellen."""
    # SSH-Tunnel einrichten
    ssh_creds = get_ssh_credentials()
    if not os.path.exists(ssh_creds['keyfile']):
        raise FileNotFoundError(f"PPK-Key nicht gefunden: {ssh_creds['keyfile']}")
    
    tunnel = SSHTunnelForwarder(
        (ssh_creds['host'], ssh_creds['port']),
        ssh_username=ssh_creds['username'],
        ssh_password=ssh_creds['password'],
        ssh_pkey=ssh_creds['keyfile'],
        remote_bind_address=('127.0.0.1', 3306),
        local_bind_address=('127.0.0.1', 3306)
    )
    tunnel.start()
    
    # Datenbankverbindung herstellen
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine), tunnel, ssh_creds['keyfile']  # Key-Datei zurückgeben

def import_data():
    """Hauptfunktion für den Import der Daten."""
    # KeePass Passwort setzen
    global KEEPASS_PASSWORD
    KEEPASS_PASSWORD = get_keepass_password()
    
    # Google Sheets Service initialisieren
    service = get_google_sheets_service()
    
    # Daten aus Google Sheets lesen
    data = get_sheet_data(service)
    if not data:
        print("Keine Daten in Google Sheets gefunden.")
        return
    
    # DataFrame aus den Daten erstellen
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # Datenbankverbindung herstellen
    Session, tunnel, key_file = setup_database()
    session = Session()
    
    try:
        # Hier kommt die Logik zum Import der Daten
        # TODO: Implementiere die Logik zum Mapping der Google Sheets Daten auf die Datenbankmodelle
        
        session.commit()
        print("Daten erfolgreich importiert.")
    except Exception as e:
        session.rollback()
        print(f"Fehler beim Import: {str(e)}")
    finally:
        session.close()
        tunnel.stop()
        # Lösche die temporäre Key-Datei
        try:
            os.unlink(key_file)
        except Exception as e:
            print(f"Warnung: Konnte temporäre Key-Datei nicht löschen: {str(e)}")

if __name__ == "__main__":
    import_data() 