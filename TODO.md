# To-Do Liste

## Backlog
- [ ] **multiuser logins** _(Low)_
- [ ] **updater** _(Medium)_
- [ ] **besseres gui** _(Medium)_
- [ ] **automatische einträge von dhl label tool** _(High)_
- [ ] **dhl tracking** _(High)_
- [ ] **DB Einträge löschen handling** _(Medium)_
- [ ] **soft delete system?** _(Medium)_
- [ ] **vorhandene Daten übertragen** _(Low)_

## Open
- [ ] **label_generator.py refactor/aufteilen** _(Low)_
- [ ] **dhl label tool styling fix** _(Low)_
- [ ] **gitguardian prüfung aktualisieren** _(Low)_

## RMA-Integration & Tracking-Nummer-Recycling (High Priority)
- [ ] **Automatische RMA-Fallerstellung bei Label-Generierung** _(High)_
  - [ ] DHL Label Tool erweitern um RMA-Case-Erstellung
  - [ ] Zendesk-Ticket-Nummer als Referenz verwenden
  - [ ] Tracking-Nummer automatisch aus Zendesk übernehmen
  - [ ] Seriennummer aus Billbee-Bestellung übernehmen
- [ ] **RMA-Datenbank erweitern um Zendesk-Integration** _(High)_
  - [ ] Zendesk-API-Client für RMA-DB implementieren
  - [ ] Automatisches Abrufen von Tracking-Nummern aus Zendesk
  - [ ] Synchronisation zwischen Zendesk und RMA-DB
- [ ] **Tracking-Nummer-Recycling-Problem lösen** _(High)_
  - [ ] Implementierung der bestehenden Zendesk-Anhängung in RMA-DB
  - [ ] Automatische Deduplizierung von Tracking-Nummern
  - [ ] Historie der Tracking-Nummer-Verwendung
- [ ] **Paket-Scan-Integration für Tracking-Nummern** _(Medium)_
  - [ ] Barcode-Scanner-Integration in RMA-DB
  - [ ] Automatische Tracking-Nummer-Erkennung
  - [ ] Validierung gegen DHL-API
- [ ] **Präsentation vorbereiten** _(Medium)_
  - [ ] Demo-Szenarien definieren
  - [ ] Tracking-Nummer-Recycling-Problem visualisieren
  - [ ] Automatisierungsvorteile dokumentieren

## Erledigt (Resolved)
- [x] **dhl label tool: label generieren ermöglichen** _(High)_
- [x] **Fehler-Logging verbessern** _(High)_
- [x] **setup_logger universell machen** _(Medium)_
- [x] **dhl label tool logging fix** _(High)_
- [x] **Problembeschreibung bug** _(High)_
- [x] **Tracking-Nummer-Recycling-Problem identifiziert und Lösung implementiert** _(High)_
  - [x] Zendesk-Integration im DHL Label Tool funktioniert
  - [x] Automatische Anhängung von Tracking-Nummern statt Überschreibung
  - [x] Vollständige Datenkonsistenz zwischen DHL, Zendesk und Billbee 