# DHL Label Tool

Das **DHL Label Tool** ist eine einfache Anwendung zur Erstellung von DHL-Versandetiketten. Es ermöglicht die automatische Verarbeitung von Bestellungen und das Generieren von Versandlabels, die lokal gespeichert werden.

## Funktionen

- **Automatischer Datenabruf:**  
  Bestellungen eines Kunden können direkt aus Billbee geladen werden.
- **Adressdatenübernahme:**  
  Die Adressdaten einer Bestellung werden automatisch in die entsprechenden Felder eingetragen.
- **Label-Erstellung:**  
  Versandetiketten werden generiert und lokal im Ordner `labels` gespeichert.
- **Automatische Sendungsnummer-Eintragung:**  
  Die generierte Sendungsnummer wird automatisch in das zugehörige Zendesk-Ticket eingetragen.

## Systemanforderungen

- Windows 10 oder neuer
- Keine zusätzlichen Installationen erforderlich – alle Ressourcen sind in der Anwendung enthalten.

## Installation

1. Lade die Datei `DHL_Label_Tool XY.exe` herunter.
2. Speichere die Datei an einem beliebigen Ort auf deinem Computer.

## Bedienung

1. Starte das Tool durch Doppelklick auf die Datei `DHL_Label_Tool.exe`.
2. Gib die **Ticketnummer** in das entsprechende Feld ein.
3. Wähle den Typ des Tickets (z. B. Bestellung oder Rücksendung), um die Buttons zu aktivieren.
4. Klicke auf **„Bestellungen abrufen“**, um die Bestellungen des Kunden aus Billbee zu laden.
5. Wähle eine Bestellung im Dropdown-Menü **„Bestellungen“** aus. Die Adressdaten der Bestellung werden automatisch in die entsprechenden Felder eingetragen.
6. Überprüfe die Daten und klicke auf **„Label generieren“**, um das Versandetikett zu erstellen.
7. Das Label wird im Ordner `labels` gespeichert, benannt nach dem Kundennamen und der Ticketnummer.
8. Die Sendungsnummer wird automatisch im zugehörigen Zendesk-Ticket eingetragen.

## Hinweise

- Der Ordner `labels` wird automatisch im gleichen Verzeichnis erstellt, in dem sich die .exe-Datei befindet.
- Stelle sicher, dass eine Internetverbindung besteht, damit die API-Dienste (Billbee und Zendesk) ordnungsgemäß funktionieren.
