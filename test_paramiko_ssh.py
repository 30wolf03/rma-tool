import paramiko
import getpass
import os
from pykeepass import PyKeePass
import tempfile

# HOST = "testserver.ilockit.bike"  # Entfernt - wird jetzt aus KeePass gelesen
# PORT = 345                       # Entfernt - wird jetzt aus KeePass gelesen
# USER = "haveltec"  # Entfernt - wird jetzt aus KeePass gelesen

# KeePass-Datenbank abfragen
kdbx_path = "modules/rma-db-gui/credentials.kdbx"
if not os.path.isfile(kdbx_path):
    print(f"Datei nicht gefunden: {kdbx_path}")
    exit(1)

master_pw = getpass.getpass("Masterpasswort für KeePass: ")

try:
    kp = PyKeePass(kdbx_path, password=master_pw)
except Exception as e:
    print(f"Fehler beim Öffnen der KeePass-Datenbank: {e}")
    exit(1)

# SSH-Eintrag suchen
entry = kp.find_entries(title="SSH", first=True)
if not entry:
    print("Kein Eintrag mit Titel 'SSH' gefunden.")
    exit(1)

# Benutzername, Passwort und Verbindungsinfo extrahieren
ssh_username = entry.username
ssh_password = entry.password
ssh_url = entry.url

if not ssh_username:
    print("Kein Benutzername im SSH-Eintrag gefunden.")
    exit(1)

if not ssh_url:
    print("Keine URL im SSH-Eintrag gefunden.")
    exit(1)

# Extrahiere Hostname und Port aus der URL (z.B. "testserver.ilockit.bike:345")
try:
    if ':' in ssh_url:
        hostname, port_str = ssh_url.split(':', 1)
        port = int(port_str)
    else:
        hostname = ssh_url
        port = 22  # Standard SSH Port
    
    print(f"Verwende Host: {hostname}, Port: {port}")
except ValueError as e:
    print(f"Fehler beim Parsen der URL '{ssh_url}': {e}")
    exit(1)

key_attachment = None
for att in entry.attachments:
    if att.filename == "traccar.key":
        key_attachment = att
        break
if not key_attachment:
    print("Anhang 'traccar.key' nicht gefunden.")
    exit(1)

# Key temporär speichern
with tempfile.NamedTemporaryFile(delete=False) as tmp_key:
    tmp_key.write(key_attachment.data)
    tmp_key_path = tmp_key.name

try:
    key = paramiko.RSAKey.from_private_key_file(tmp_key_path, password=ssh_password)
except paramiko.PasswordRequiredException:
    print("Der Private Key ist passwortgeschützt, aber keine Passphrase wurde angegeben.")
    os.unlink(tmp_key_path)
    exit(1)
except paramiko.SSHException as e:
    print(f"Fehler beim Laden des Private Keys: {e}")
    os.unlink(tmp_key_path)
    exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Verbinde zu {ssh_username}@{hostname}:{port} ...")
    client.connect(
        hostname=hostname,
        port=port,
        username=ssh_username,
        pkey=key,
        timeout=10
    )
    print("Verbindung erfolgreich!")
    stdin, stdout, stderr = client.exec_command("whoami")
    print("Remote-Ausgabe:", stdout.read().decode().strip())
except Exception as e:
    print(f"SSH-Verbindung fehlgeschlagen: {e}")
finally:
    client.close()
    os.unlink(tmp_key_path)
    print("Verbindung geschlossen.") 