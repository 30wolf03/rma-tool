# RMA Database GUI

Eine grafische Benutzeroberfläche für die Verwaltung der RMA-Datenbank.

## Installation

1. Stelle sicher, dass Python 3.8 oder höher installiert ist.
2. Installiere die erforderlichen Abhängigkeiten:

```bash
pip install -r requirements.txt
```

3. Kopiere die `credentials.kdbx` Datei in das Modulverzeichnis.

## Verwendung

1. Starte die Anwendung:

```bash
python -m modules.rma-db-gui.gui.main_window
```

2. Gib das KeePass Master-Passwort ein und klicke auf "Connect".
3. Nach erfolgreicher Verbindung werden die RMA-Daten in einer Tabelle angezeigt.

## Sicherheit

- Die Verbindungsdaten werden sicher in einer KeePass-Datenbank gespeichert.
- Die SSH-Verbindung verwendet einen privaten Schlüssel.
- Das Master-Passwort wird nur im Speicher gehalten und nicht persistent gespeichert.

## Entwicklung

Das Modul ist in folgende Komponenten aufgeteilt:

- `config/settings.py`: Konfigurationskonstanten
- `database/connection.py`: Datenbankverbindung mit SSH-Tunnel
- `gui/main_window.py`: Hauptfenster der GUI
- `utils/keepass_handler.py`: Handler für KeePass-Zugriff

## Lizenz

Proprietär - Alle Rechte vorbehalten. 