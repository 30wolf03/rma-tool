# RMA-Datenbank-GUI - Präsentationsleitfaden

##  Übersicht
Die RMA-Datenbank-GUI ist eine benutzerfreundliche Oberfläche für die Verwaltung von RMA-Fällen (Return Merchandise Authorization) mit vollständiger CRUD-Funktionalität.

##  Hauptfunktionen

###  CRUD-Operationen (Create, Read, Update, Delete)
- **Create**: Neue RMA-Einträge erstellen über "Neuen Eintrag erstellen" Button
- **Read**: Alle RMA-Fälle in übersichtlicher Tabelle anzeigen
- **Update**: Einträge direkt in der Tabelle oder über "Eintrag bearbeiten" Button
- **Delete**: Soft-Delete (Archivierung) mit Wiederherstellungsmöglichkeit

###  Suchfunktion
- Echtzeit-Suche in Ticket-Nummer, Auftragsnummer und Produktname
- Filtert die Tabelle automatisch während der Eingabe
- "X" Button zum Löschen der Suche

###  Datenverwaltung
- **Aktive Einträge**: Normale Ansicht aller aktiven RMA-Fälle
- **Papierkorb**: Archivierte Einträge mit Wiederherstellungsoption
- **Sortierung**: Klick auf Spaltenüberschriften für Sortierung
- **Kontextmenü**: Rechtsklick für zusätzliche Optionen

###  Benutzerfreundlichkeit
- **Dropdown-Menüs**: Für Status, Typ, Lagerort und Bearbeiter
- **Validierung**: Automatische Überprüfung der Eingaben
- **Status-Bar**: Aktuelle Informationen und Feedback
- **Fehlerbehandlung**: Benutzerfreundliche Fehlermeldungen

##  Datenbankstruktur

### Haupttabelle: RMA_Cases
- `TicketNumber`: Zendesk Ticket-Nummer (Primärschlüssel)
- `OrderNumber`: Auftragsnummer aus Billbee/Shopify/Amazon
- `Type`: Typ (Reparatur, Widerruf, Ersatz, Rückerstattung, Sonstiges)
- `EntryDate`: Eingangsdatum
- `Status`: Status (Open, In Progress, Completed)
- `StorageLocation`: Lagerort
- `ExitDate`: Ausgangsdatum
- `TrackingNumber`: Tracking-Nummer
- `IsAmazon`: Amazon-Bestellung (Boolean)

### Untertabellen
- **RMA_Products**: Produktinformationen (Name, Seriennummer, Menge)
- **RMA_RepairDetails**: Reparaturdetails (Kundenbeschreibung, Problemursache, Letzte Aktion)
- **RMA_ReturnDetails**: Rückgabedetails (Grund, Letzter Bearbeiter)

### Referenztabellen
- **Handlers**: Bearbeiter (Initials, Name)
- **StorageLocations**: Lagerorte (ID, LocationName)
- **ProblemCauses**: Problemursachen (ID, Description)

##  Verwendung

### 1. Anmeldung
- KeePass Master Password eingeben
- "Connect" Button klicken

### 2. Neue Einträge erstellen
- "Neuen Eintrag erstellen" Button klicken
- Pflichtfelder ausfüllen (Ticket-Nummer, Auftragsnummer)
- Optionale Felder nach Bedarf
- "OK" zum Speichern

### 3. Einträge bearbeiten
- Zeile in der Tabelle auswählen
- "Eintrag bearbeiten" Button oder Doppelklick
- Änderungen vornehmen
- "OK" zum Speichern

### 4. Einträge löschen (Archivieren)
- Einträge auswählen
- "Löschen" Button oder Kontextmenü
- Bestätigung erforderlich
- Einträge werden in Papierkorb verschoben

### 5. Papierkorb verwalten
- "Papierkorb anzeigen" Button für archivierte Einträge
- "Wiederherstellen" für Wiederherstellung
- "Endgültig löschen" für permanente Löschung

##  Integration
- **SSH-Tunnel**: Sichere Verbindung zur Antares-Datenbank
- **KeePass-Integration**: Sichere Credential-Verwaltung
- **DHL Label Tool**: Zusammenarbeit mit dem DHL-Label-System

##  Technische Details
- **Framework**: PySide6 (Qt für Python)
- **Datenbank**: MySQL über SSH-Tunnel
- **Architektur**: MVC-Pattern mit Clean Code
- **Logging**: Umfassendes Logging-System
- **Error Handling**: Robuste Fehlerbehandlung

##  Best Practices
- **PEP-8**: Vollständige Code-Konformität
- **Type Hints**: Vollständige Typisierung
- **Docstrings**: Umfassende Dokumentation
- **Exception Handling**: Sichere Fehlerbehandlung
- **User Experience**: Intuitive Benutzeroberfläche

##  Demo-Szenarien für Präsentation

### Szenario 1: Neuen RMA-Fall erstellen
1. "Neuen Eintrag erstellen" klicken
2. Ticket-Nummer eingeben (z.B. "DEMO-001")
3. Auftragsnummer eingeben (z.B. "ORDER-123")
4. Typ auswählen (z.B. "Reparatur")
5. Produktinformationen eingeben
6. Speichern und Erfolgsmeldung zeigen

### Szenario 2: Eintrag bearbeiten
1. Bestehenden Eintrag auswählen
2. "Eintrag bearbeiten" klicken
3. Status ändern (z.B. "In Progress")
4. Bearbeiter zuweisen
5. Speichern und Änderungen zeigen

### Szenario 3: Suche und Filterung
1. Suchbegriff eingeben (z.B. "DEMO")
2. Tabelle wird automatisch gefiltert
3. Status-Bar zeigt Anzahl der Ergebnisse
4. "X" Button zum Zurücksetzen

### Szenario 4: Archivierung und Wiederherstellung
1. Eintrag auswählen und löschen
2. Papierkorb-Ansicht zeigen
3. Eintrag wiederherstellen
4. Zurück zu aktiven Einträgen

##  Fazit
Die RMA-Datenbank-GUI bietet eine vollständige, benutzerfreundliche Lösung für die Verwaltung von RMA-Fällen mit moderner Technologie und bewährten Praktiken. 