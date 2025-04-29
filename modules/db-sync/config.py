import os
from pykeepass import PyKeePass
import tempfile

# KeePass Konfiguration
KEEPASS_DB_PATH = os.path.join(os.path.dirname(__file__), 'credentials.kdbx')
KEEPASS_PASSWORD = None  # Wird zur Laufzeit abgefragt

def get_keepass_credentials(entry_path):
    """Holt Credentials aus der KeePass Datenbank."""
    try:
        kp = PyKeePass(KEEPASS_DB_PATH, password=KEEPASS_PASSWORD)
        entry = kp.find_entries(path=entry_path, first=True)
        if entry:
            return {
                'username': entry.username,
                'password': entry.password,
                'url': entry.url,
                'notes': entry.notes,
                'binary': entry.binary  # Für den PPK-Key
            }
        return None
    except Exception as e:
        print(f"Fehler beim Zugriff auf KeePass: {str(e)}")
        return None

# Google Sheets Konfiguration
GOOGLE_SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
GOOGLE_SHEETS_RANGE = 'A:Z'  # Anpassen je nach Bedarf

def get_google_sheets_id():
    """Holt die Google Sheets ID aus KeePass."""
    creds = get_keepass_credentials('RMA-Tool/Google Sheets')
    return creds.get('url') if creds else None

GOOGLE_SHEETS_SPREADSHEET_ID = get_google_sheets_id()

# SSH und MySQL Konfiguration
def get_ssh_credentials():
    """Holt SSH-Credentials aus KeePass."""
    creds = get_keepass_credentials('RMA-Tool/SSH')
    if creds:
        # Erstelle temporäre Datei für den PPK-Key
        temp_key_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ppk')
        temp_key_file.write(creds['binary'])
        temp_key_file.close()
        
        return {
            'host': creds.get('url'),
            'port': 22,  # Standard SSH Port
            'username': creds.get('username'),
            'password': creds.get('password'),
            'keyfile': temp_key_file.name  # Temporärer Pfad zum PPK-Key
        }
    return None

def get_mysql_credentials():
    """Holt MySQL-Credentials aus KeePass."""
    creds = get_keepass_credentials('RMA-Tool/MySQL')
    if creds:
        return {
            'host': 'localhost',  # Lokal wegen SSH-Tunnel
            'port': 3306,  # Standard MySQL Port
            'database': creds.get('username'),
            'user': creds.get('username'),
            'password': creds.get('password')
        }
    return None

# Datenbank URL
def get_database_url():
    """Erstellt die MySQL-URL aus den KeePass Credentials."""
    mysql_creds = get_mysql_credentials()
    if mysql_creds:
        return f"mysql+pymysql://{mysql_creds['user']}:{mysql_creds['password']}@{mysql_creds['host']}:{mysql_creds['port']}/{mysql_creds['database']}"
    return None

DATABASE_URL = get_database_url() 