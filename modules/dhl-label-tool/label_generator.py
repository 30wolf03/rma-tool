import os
import time
import base64
import json
import requests
import utils
import sys
import traceback
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLineEdit, 
                            QPushButton, QFormLayout, QTextEdit, QMessageBox,
                            QInputDialog, QComboBox, QLabel, QHBoxLayout, QCheckBox, QShortcut, QDockWidget, QApplication)

from zendesk_api import get_customer_email, update_problem_description, update_serial_number, update_order_info
from billbee_api import BillbeeAPI
from utils import setup_logger, BlockFormatter, validate_inputs, validate_reference_number
from preview_window import PreviewWindow
from dhl_api import DHLAPI as DHL_API_CLASS
from datetime import datetime

# Globaler Exception Handler
def global_exception_handler(exctype, value, tb):
    """Globaler Exception Handler für unbehandelte Ausnahmen"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    
    # Erstelle das Log-Verzeichnis im gleichen Verzeichnis wie die ausführbare Datei
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Schreibe den Fehler in eine Crash-Log-Datei
    crash_log_path = os.path.join(log_dir, "crash.log")
    try:
        with open(crash_log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n=== Crash Report {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(error_msg)
    except:
        pass  # Wenn selbst das Schreiben des Crash-Logs fehlschlägt, können wir nichts mehr tun
    
    # Zeige eine Fehlermeldung an
    try:
        app = QApplication.instance()
        if app:
            QMessageBox.critical(None, "Kritischer Fehler",
                               f"Ein unerwarteter Fehler ist aufgetreten:\n\n{str(value)}\n\n"
                               f"Details wurden in {crash_log_path} gespeichert.")
    except:
        pass
    
    # Beende die Anwendung
    sys.exit(1)

# Setze den globalen Exception Handler
sys.excepthook = global_exception_handler

class DHLLabelGenerator(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.logger = setup_logger()
            self.logger.info("Starte Initialisierung der Anwendung")
            
            # Setze den Fenstertitel
            self.setWindowTitle("DHL Label Tool 16")
            
            # API Credentials
            self.username = None
            self.password = None
            self.client_id = None
            self.client_secret = None
            self.zendesk_email = None
            self.zendesk_token = None
            self.billing_number = None
            self.bb_api_key = None
            self.bb_api_user = None
            self.bb_api_password = None
            self.dhl_api = None

            # Eingabefelder erstellen
            self.ticket_nr_input = QLineEdit()
            self.type_dropdown = QComboBox()
            self.type_dropdown.addItems(["- Bitte auswählen -", "Widerruf", "Reparatur", "Test"])
            self.name_input = QLineEdit()
            self.street_input = QLineEdit()
            self.house_input = QLineEdit()
            self.additional_info_input = QLineEdit()
            self.postal_input = QLineEdit()
            self.city_input = QLineEdit()
            self.email_input = QLineEdit()
            self.email_input.returnPressed.connect(self.handle_email_enter)
            self.phone_input = QLineEdit()
            self.ref_input = QLineEdit()
            #Gewichtsfeld hinzufügen
            self.weight_input = QLineEdit()
            self.weight_input.setPlaceholderText("1000")
            
            # Problembeschreibungsfeld hinzufügen
            self.problem_description = QLineEdit()
            self.problem_description.setPlaceholderText("Problembeschreibung eingeben...")
            
            # Direkt nach dem E-Mail-Feld im Formular hinzufügen:
            self.address_dropdown = QComboBox()
            # Shortcut definieren, der im gesamten Fenster gilt:
            self.enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
            self.enter_shortcut.activated.connect(self.trigger_fetch_action)
            # Verbinde den Dropdown-Änderungssignal mit einem Slot:
            self.address_dropdown.currentIndexChanged.connect(self.on_address_selected)
            
            # Signal-Slot-Verbindung für dynamisches Update der Referenz:
            self.ticket_nr_input.textChanged.connect(self.update_reference_field)
            
            # Bestellungen Dropdown
            self.orders_dropdown = QComboBox()
            self.orders_dropdown.addItem("- Bitte auswählen -")
            self.orders_dropdown.currentIndexChanged.connect(self.on_order_selected)

            # Layout erstellen
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            form_layout = QFormLayout()

            # Ticket Layout
            ticket_layout = QHBoxLayout()
            ticket_layout.addWidget(QLabel("Ticket Nr."))
            ticket_layout.addWidget(self.ticket_nr_input)
            ticket_layout.addWidget(QLabel("Typ"))
            ticket_layout.addWidget(self.type_dropdown)
            self.email_button = QPushButton("Bestellungen abrufen")
            self.email_button.clicked.connect(self.fetch_customer_data)
            self.email_button.setEnabled(False)
            ticket_layout.addWidget(self.email_button)
            form_layout.addRow("", ticket_layout)

            # Formular Layout
            form_layout.addRow("Bestellungen:", self.orders_dropdown)
            form_layout.addRow("Name:", self.name_input)
            form_layout.addRow("Straße:", self.street_input)
            form_layout.addRow("Hausnummer:", self.house_input)
            form_layout.addRow("Zusatz:", self.additional_info_input)
            form_layout.addRow("PLZ:", self.postal_input)
            form_layout.addRow("Stadt:", self.city_input)
            form_layout.addRow("Gewicht (g):", self.weight_input)
            form_layout.addRow("Problembeschreibung:", self.problem_description)
            

            # Email Layout
            email_layout = QHBoxLayout()
            email_layout.addWidget(self.email_input)
            self.address_button = QPushButton("Bestellungen abrufen")
            self.address_button.clicked.connect(self.fetch_orders)
            self.address_button.setEnabled(True)
            email_layout.addWidget(self.address_button)
            form_layout.addRow("E-Mail:", email_layout)
            form_layout.addRow("Telefon:", self.phone_input)
            form_layout.addRow("Referenz:", self.ref_input)
            

            # Log Bereich
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            
            # Füge den GUI-Handler zum Logger hinzu
            from utils import add_gui_handler
            self.logger = add_gui_handler(self.log_text)

            # Button Layout
            button_layout = QHBoxLayout()
            self.clear_fields_checkbox = QCheckBox("Felder automatisch leeren")
            self.clear_fields_checkbox.setChecked(True)
            self.clear_fields_checkbox.stateChanged.connect(self.on_clear_fields_changed)
            
            self.generate_button = QPushButton("Label generieren")
            self.generate_button.clicked.connect(self.generate_label)
            self.generate_button.setEnabled(False)
            self.clear_fields_button = QPushButton("Alle leeren")
            self.clear_fields_button.setFixedSize(100, 30)
            self.clear_fields_button.clicked.connect(lambda: utils.clear_all_fields(self))
            
            # Neuer Button für Seriennummer-Extraktion
            self.extract_serial_button = QPushButton("Seriennummer extrahieren")
            self.extract_serial_button.clicked.connect(self.extract_and_update_serial)
            self.extract_serial_button.setEnabled(False)
            
            button_layout.addWidget(self.clear_fields_checkbox)
            button_layout.addStretch()
            button_layout.addWidget(self.extract_serial_button)
            button_layout.addWidget(self.generate_button)
            button_layout.addWidget(self.clear_fields_button)

            # Verbindung mit Dropdown
            self.type_dropdown.currentIndexChanged.connect(self.check_type_selection)
            self.type_dropdown.currentIndexChanged.connect(self.update_reference_field)
            
            # Layout zusammenbauen
            layout.addLayout(form_layout)
            layout.addWidget(self.log_text)
            layout.addLayout(button_layout)
            
            self.log_text.append("Buttons deaktiviert, bitte einen Typ auswählen")
            
            # Erstelle den Vorschau-Button
            self.preview_button = QPushButton("Vorschau anzeigen", self)
            self.preview_button.clicked.connect(self.toggle_preview)
            
            # Füge den Button ins Layout ein
            layout.addWidget(self.preview_button)
            
            # Vorschaufenster initial als None
            self.preview_window = None

            # Verbinde die relevanten Eingabefelder mit der Methode zum Aktualisieren der Vorschau
            self.name_input.textChanged.connect(self.update_preview_content)
            self.street_input.textChanged.connect(self.update_preview_content)
            self.house_input.textChanged.connect(self.update_preview_content)
            self.postal_input.textChanged.connect(self.update_preview_content)
            self.city_input.textChanged.connect(self.update_preview_content)
            self.ref_input.textChanged.connect(self.update_preview_content)
            self.weight_input.textChanged.connect(self.update_preview_content)
            
            self.logger.info("Initialisierung abgeschlossen")

        except Exception as e:
            self.logger.error(f"Fehler bei der Initialisierung: {str(e)}")
            QMessageBox.critical(self, "Fehler", str(e))

    def toggle_preview(self):
        """Öffnet oder schließt das Vorschaufenster und aktualisiert die Inhalte bei jedem Öffnen."""
        if self.preview_window is None:
            # Erstelle das Vorschaufenster
            self.preview_window = PreviewWindow()
            self.update_preview_position()  # Positioniere das Fenster rechts vom Hauptfenster
        self.update_preview_content()  # Aktualisiere die Vorschauinhalte direkt beim Öffnen
        if not self.preview_window.isVisible():
            self.preview_window.show()
            self.preview_button.setText("Vorschau ausblenden")
        else:
            self.preview_window.hide()
            self.preview_button.setText("Vorschau anzeigen")
            
    def closeEvent(self, event):
        if self.preview_window is not None:
            self.preview_window.close()
        super().closeEvent(event)

    def moveEvent(self, event):
        """Wird ausgelöst, wenn das Hauptfenster bewegt wird."""
        super().moveEvent(event)
        if self.preview_window and self.preview_window.isVisible():
            self.update_preview_position()

    def update_preview_position(self):
        """Positioniert das Vorschaufenster rechts vom Hauptfenster."""
        if self.preview_window:
            main_geo = self.geometry()  # Geometrie des Hauptfensters
            x = main_geo.x() + main_geo.width() + 10  # Rechts vom Hauptfenster mit 10px Abstand
            y = main_geo.y()  # Gleiche Y-Position wie das Hauptfenster
            self.preview_window.move(x, y)
    
    def update_preview_content(self):
        """Sammelt Eingabedaten und aktualisiert die Vorschau."""
        if self.preview_window:
            # Absenderadresse aus den Eingabefeldern (Name, Straße, Hausnummer, PLZ, Stadt)
            sender = f"{self.name_input.text().strip()}\n" \
                    f"{self.street_input.text().strip()} {self.house_input.text().strip()}\n" \
                    f"{self.postal_input.text().strip()} {self.city_input.text().strip()}"

            reference = self.ref_input.text().strip()
            
            # Gewicht aus dem Eingabefeld
            weight_gram = self.weight_input.text().strip()
            if not weight_gram:
                weight_gram = 1000  # Standardgewicht in Gramm verwenden
            else:
                try:
                    weight_gram = int(weight_gram)
                except ValueError:
                    weight_gram = 1000  # Fallback auf Standardgewicht bei ungültiger Eingabe

            # Umrechnung in Kilogramm
            weight_kg = weight_gram / 1000

            text_data = {
                "sender": sender,
                "reference": reference,
                "weight": f"{weight_kg:.2f}"  # Gewicht mit zwei Dezimalstellen für kg
            }

            # Aktualisiere die Vorschau im Fenster
            self.preview_window.update_preview(text_data)
            
    def trigger_fetch_action(self):
        """
        Löst den Klick des Kombinationsbuttons aus,
        sofern dieser enabled ist.
        """
        if self.email_button.isEnabled():
            self.email_button.click()
        
    def check_type_selection(self):
        """
        Aktiviert den Generate-Button nur, wenn der ausgewählte Typ nicht der Platzhalter ist.
        """
        if self.type_dropdown.currentText() == "- Bitte auswählen -":
            self.generate_button.setEnabled(False)
            self.email_button.setEnabled(False)
            self.extract_serial_button.setEnabled(False)
            self.logger.info("Buttons deaktiviert, bitte einen Typ auswählen")
            self.logger.info("-" * 80)
        else:
            self.generate_button.setEnabled(True)
            self.email_button.setEnabled(True)
            self.extract_serial_button.setEnabled(True)
            self.logger.info("Typ ausgewählt, Buttons aktiviert")
            self.logger.info("-" * 80)
    
    def fetch_orders(self) -> None:
        """
        Ruft alle Bestellungen für eine E-Mail-Adresse von Billbee ab.

        Diese Methode:
        1. Prüft ob eine E-Mail-Adresse eingegeben wurde
        2. Initialisiert die Billbee-API mit den gespeicherten Zugangsdaten
        3. Ruft alle Bestellungen für diese E-Mail ab
        4. Befüllt das Bestellungen-Dropdown mit den gefundenen Daten
        5. Zeigt Gewicht und Seriennummer (falls vorhanden) in der Bestellübersicht

        Returns:
            None
        """
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, "Fehler", "Bitte eine E-Mail-Adresse eingeben.")
            return

        try:
            billbee = BillbeeAPI(
                api_key=self.bb_api_key,
                api_user=self.bb_api_user,
                api_password=self.bb_api_password
            )
            orders = billbee.get_all_customer_orders(email)

            self.orders_dropdown.clear()
            self.orders_dropdown.addItem("- Bitte auswählen -")
            
            if orders:
                for order in orders:
                    order_number = order.get("OrderNumber", "Unbekannt")
                    weight_kg = order.get("ShipWeightKg")
                    
                    if weight_kg is not None:
                        weight_gram = int(float(weight_kg) * 1000)
                        order_text = (
                            f"Bestellnummer: {order_number} - "
                            f"Gewicht: {weight_gram}g"
                        )
                    else:
                        order_text = f"Bestellnummer: {order_number}"

                    # Extrahiere die Seriennummer aus den Notizen
                    notes = order.get("SellerComment", "")
                    if notes:
                        serial_number = billbee.extract_serial_number(notes)
                        if serial_number:
                            order_text += f" - Seriennummer: {serial_number}"

                    self.orders_dropdown.addItem(order_text, order)
                    
                self.logger.info(f"{len(orders)} Bestellungen erfolgreich geladen")
                self.logger.info("-" * 80)
                
                # Dropdown kurz grün aufleuchten lassen
                self.orders_dropdown.setStyleSheet("background-color: lightgreen;")
                QTimer.singleShot(
                    2000, 
                    lambda: self.orders_dropdown.setStyleSheet("")
                )
            else:
                QMessageBox.warning(self, "Fehler", "Keine Bestellungen gefunden.")
                self.logger.info("Keine Bestellungen gefunden")
                self.logger.info("-" * 80)
                
        except Exception as e:
            QMessageBox.warning(
                self, 
                "Fehler", 
                f"Fehler beim Abrufen der Bestellungen: {str(e)}"
            )

    def on_order_selected(self, index):
        if index == 0:  # Platzhalter ignorieren
            return

        selected_order = self.orders_dropdown.itemData(index)
        if selected_order:
            # Adressdaten aus der Bestellung laden
            shipping_address = selected_order.get("ShippingAddress", {})
            country = shipping_address.get("Country", "").strip()
            # Gewicht berechnen: wenn "ShipWeightKg" vorhanden ist, in Gramm umrechnen
            weight_kg = selected_order.get("ShipWeightKg")
            if weight_kg is not None:
                try:
                    weight_gram = int(float(weight_kg) * 1000)
                except (ValueError, TypeError):
                    weight_gram = None
            else:
                weight_gram = None
                        
            # Überprüfen, ob das Land nicht Deutschland ist
            if country != "DE":
                QMessageBox.warning(
                    self,
                    "Warnung",
                    f"Die ausgewählte Bestellung stammt aus {country}. \n"
                    "Die DHL-API unterstützt nur nationale Labels."
                )
                # Deaktivieren der Label-Erstellung
                self.generate_button.setEnabled(False)
            else:
                # Aktivieren der Label-Erstellung für deutsche Bestellungen
                self.generate_button.setEnabled(True)

            # Nur übernehmen, wenn das Gewicht > 1000g ist, ansonsten das Feld leer lassen
            if weight_gram is not None and weight_gram > 1000:
                self.weight_input.setText(str(weight_gram))
                self.logger.info(f"Gewicht aus Bestellung übernommen: {weight_gram}g")
            else:
                self.weight_input.clear()
                self.logger.info("Bestellgewicht < 1000g, Standardgewicht wird verwendet.")
            
            # Kombiniere Vor- und Nachname, sofern vorhanden
            firstname = shipping_address.get("FirstName", "")
            lastname = shipping_address.get("LastName", "")
            full_name = f"{firstname} {lastname}".strip()
            self.name_input.setText(full_name)
            self.street_input.setText(shipping_address.get("Street", ""))
            self.house_input.setText(shipping_address.get("HouseNumber", ""))
            self.postal_input.setText(shipping_address.get("Zip", ""))
            self.city_input.setText(shipping_address.get("City", ""))
            # Optional: Telefon übernehmen, falls vorhanden
            phone = shipping_address.get("Phone")
            if phone is None:
                phone = ""
            self.phone_input.setText(str(phone))
            
            self.logger.info(f"Adressdaten aus Bestellung übernommen: {full_name}, {shipping_address.get('Street', '')} {shipping_address.get('HouseNumber', '')}, {shipping_address.get('Zip', '')} {shipping_address.get('City', '')}")
            
            # Extrahiere die Seriennummer aus den Notizen
            notes = selected_order.get("SellerComment", "")
            if notes:
                # Initialisiere die Billbee-API falls noch nicht geschehen
                if not hasattr(self, 'bb_api') or self.bb_api is None:
                    self.bb_api = BillbeeAPI(
                        api_key=self.bb_api_key,
                        api_user=self.bb_api_user,
                        api_password=self.bb_api_password
                    )
                
                serial_number = self.bb_api.extract_serial_number(notes)
                if serial_number:
                    self.logger.info(f"Seriennummer gefunden: {serial_number}")
                    # Aktualisiere das Referenzfeld mit der Seriennummer
                    self.update_reference_field(serial_number)
                else:
                    self.logger.info("Keine Seriennummer in den Notizen gefunden")
                    self.update_reference_field()
            else:
                self.logger.info("Keine Notizen für die Bestellung gefunden")
                self.update_reference_field()

    def get_zendesk_email(self):
        ticket_id = self.ticket_nr_input.text()
        if ticket_id:
            try:
                email = get_customer_email(ticket_id, self.zendesk_email, self.zendesk_token)
                if email:
                    self.email_input.setText(email)
                    self.logger.info(f"E-Mail für Ticket {ticket_id} erfolgreich abgerufen: {email}")
                    self.logger.info("-" * 80)
                else:
                    QMessageBox.warning(self, "Fehler", "E-Mail-Adresse konnte nicht gefunden werden")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", str(e))
                self.logger.error(f"Fehler beim Abrufen der E-Mail: {str(e)}")
                self.logger.info("-" * 80)
        else:
            QMessageBox.warning(self, "Fehler", "Bitte eine Ticket-Nr. eingeben")
            self.logger.info("-" * 80)

    def handle_email_enter(self):
        """Behandelt Enter-Taste im E-Mail-Feld"""
        if not self.email_input.text():
            # Wenn E-Mail-Feld leer ist, E-Mail abrufen
            self.get_zendesk_email()
        else:
            # Wenn E-Mail vorhanden ist, Adresse abrufen
            self.get_billbee_address()

    def get_billbee_address(self):
        if not self.bb_api_key or not self.bb_api_user or not self.bb_api_password:
            QMessageBox.warning(self, "Fehler", "Keine gültigen Billbee-Zugangsdaten vorhanden")
            return
            
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, "Fehler", "Bitte eine E-Mail-Adresse eingeben")
            return
            
        try:
            billbee = BillbeeAPI(
                api_key=self.bb_api_key,
                api_user=self.bb_api_user,
                api_password=self.bb_api_password
            )
            addresses = billbee.get_all_customer_addresses(email)
            
            self.address_dropdown.clear()
            
            if addresses:
                # Fülle das Dropdown mit einer kompakten Darstellung:
                for addr in addresses:
                    street = addr.get("Street", "")
                    housenumber = addr.get("Housenumber", "")
                    city = addr.get("City", "")
                    display_text = f"{street} {housenumber}, {city}"
                    # Speichere das komplette Address-Dictionary als "userData" im Combo-Box-Item
                    self.address_dropdown.addItem(display_text, addr)

                self.logger.info("Adressen von Billbee erfolgreich geladen. Bitte wählen Sie eine Adresse aus.")
            else:
                QMessageBox.warning(self, "Fehler", "Keine Kundendaten gefunden")
        except Exception as e:
            QMessageBox.warning(self, "Fehler", str(e))
            self.logger.error(f"Fehler beim Laden der Adressdaten: {str(e)}")

    def fetch_customer_data(self) -> None:
        """
        Kombiniert den Abruf der E-Mail-Adresse aus Zendesk und der Bestellungen aus Billbee.

        Diese Methode führt folgende Schritte aus:
        1. Abruf der E-Mail-Adresse anhand der Ticketnummer aus Zendesk
        2. Abruf aller Bestellungen zu dieser E-Mail aus Billbee
        3. Befüllung des Bestellungen-Dropdowns mit den gefundenen Daten

        Returns:
            None
        """
        ticket_id = self.ticket_nr_input.text().strip()
        if not ticket_id:
            QMessageBox.warning(self, "Fehler", "Bitte eine Ticket-Nr. eingeben")
            return

        # Abruf der E-Mail-Adresse über Zendesk
        try:
            self.logger.info(f"Versuche E-Mail-Adresse für Ticket {ticket_id} abzurufen")
            self.logger.info("-" * 80)
            email = get_customer_email(ticket_id, self.zendesk_email, self.zendesk_token)
            if not email:
                QMessageBox.warning(
                    self, 
                    "Fehler", 
                    f"Keine E-Mail-Adresse zu Ticket #{ticket_id} gefunden"
                )
                self.logger.info(f"Keine E-Mail-Adresse zu Ticket {ticket_id} gefunden")
                self.logger.info("-" * 80)
                return
            self.email_input.setText(email)
            self.logger.info(
                f"E-Mail-Adresse für Ticket {ticket_id} erfolgreich abgerufen: {email}"
            )
            self.logger.info("-" * 80)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Abrufen der E-Mail: {str(e)}")
            self.logger.error(f"Fehler beim Abrufen der E-Mail: {str(e)}")
            self.logger.info("-" * 80)
            return
        
        # Abruf der Bestellungen aus Billbee basierend auf der abgerufenen E-Mail
        self.fetch_orders()

    def update_reference_field(self, serial_number=None):
        """
        Aktualisiert das Referenzfeld dynamisch basierend auf der Ticketnummer,
        der Typ-Auswahl und der Seriennummer.
        """
        ticket = self.ticket_nr_input.text().strip()
        typ_text = self.type_dropdown.currentText()

        # Wenn Ticketnummer leer ist oder noch der Platzhalter ausgewählt wurde, Referenz leeren:
        if not ticket or typ_text == "- Bitte auswählen -":
            self.ref_input.setText("")
            return

        # Bestimme den Typ-Code basierend auf dem ausgewählten Typ
        if typ_text == "Widerruf":
            typ = "WR"
            # Hole die Bestellnummer aus dem ausgewählten Bestellungs-Dropdown
            order_index = self.orders_dropdown.currentIndex()
            if order_index > 0:  # Wenn eine Bestellung ausgewählt ist (nicht der Platzhalter)
                selected_order = self.orders_dropdown.itemData(order_index)
                if selected_order and "OrderNumber" in selected_order:
                    order_number = selected_order["OrderNumber"]
                    # Baue die Referenz mit Seriennummer
                    if serial_number:
                        reference = f"#{ticket} {typ} {order_number} {serial_number}"
                    else:
                        reference = f"#{ticket} {typ} {order_number}"
                    # Prüfe, ob die Gesamtlänge unter 35 Zeichen liegt (DHL Limit)
                    if len(reference) <= 35:
                        self.ref_input.setText(reference)
                        return
        elif typ_text == "Reparatur":
            typ = "Rep"
        elif typ_text == "Test":
            typ = "test"
        else:
            typ = typ_text.upper()

        # Baue die Referenz mit Seriennummer
        if serial_number:
            reference = f"#{ticket} {typ} {serial_number}"
        else:
            reference = f"#{ticket} {typ}"

        # Prüfe, ob die Gesamtlänge unter 35 Zeichen liegt (DHL Limit)
        if len(reference) <= 35:
            self.ref_input.setText(reference)
        else:
            # Wenn die Referenz zu lang ist, kürze die Seriennummer
            if serial_number:
                max_length = 35 - len(f"#{ticket} {typ} ")
                shortened_serial = serial_number[:max_length]
                self.ref_input.setText(f"#{ticket} {typ} {shortened_serial}")
            else:
                self.ref_input.setText(f"#{ticket} {typ}")

    def on_address_selected(self, index):
        if index < 0:
            return
        address = self.address_dropdown.itemData(index)
        if address:
            # Setze die Felder mit den abgerufenen Daten
            # Falls FirstName und LastName vorhanden sind, kombiniere sie:
            firstname = address.get("FirstName", "")
            lastname = address.get("LastName", "")
            full_name = f"{firstname} {lastname}".strip()
            self.name_input.setText(full_name)
            self.street_input.setText(address.get("Street", ""))
            self.house_input.setText(address.get("Housenumber", ""))
            self.postal_input.setText(address.get("Zip", ""))
            self.city_input.setText(address.get("City", ""))
            self.phone_input.setText(address.get("Tel1", ""))
            if address.get("Company"):
                self.additional_info_input.setText(address.get("Company"))

    def initialize_dhl_api(self):
        if not hasattr(self, 'dhl_api') or self.dhl_api is None:
            self.logger.info("Initialisiere DHL API")
            self.dhl_api = DHL_API_CLASS(
                username=self.username,
                password=self.password,
                client_id=self.client_id,
                client_secret=self.client_secret,
                billing_number=self.billing_number
            )
            self.logger.info("DHL API erfolgreich initialisiert")
            self.logger.info("DHL Zugangsdaten geladen")
            self.logger.info("DHL Client Credentials geladen")
    
    def update_zendesk_ticket_fields(self, ticket_id, fields_update):
        """
        Aktualisiert mehrere Zendesk-Ticketfelder in einem API-Aufruf.

        :param ticket_id: ID des Zendesk-Tickets
        :param fields_update: Dictionary mit Feld-IDs (int) als Schlüssel und den neuen Werten (str) als Werte
        :return: True bei Erfolg, sonst False
        """
        try:
            auth_string = f"{self.zendesk_email}/token:{self.zendesk_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json"
            }
            url = f"https://ilockit.zendesk.com/api/v2/tickets/{ticket_id}.json"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            ticket_data = response.json()

            # Sichere Übernahme der aktuellen Feldwerte: None wird zu einem leeren String
            current_fields = {
                field["id"]: (field.get("value") or "")
                for field in ticket_data["ticket"]["custom_fields"]
            }

            new_fields = []
            for field_id, new_value in fields_update.items():
                # Beim Tracking-Feld wird der neue Wert angehängt
                if field_id == 18851720152732:
                    current_value = current_fields.get(field_id, "")
                    if current_value.strip():
                        combined_value = f"{current_value.strip()}\n{new_value}"
                    else:
                        combined_value = f"{new_value}"
                    new_fields.append({"id": field_id, "value": combined_value})
                # Beim Bestellnamen-Feld wird der Wert direkt gesetzt
                elif field_id == 7566313720220:
                    new_fields.append({"id": field_id, "value": new_value})
                else:
                    new_fields.append({"id": field_id, "value": new_value})

            update_data = {"ticket": {"custom_fields": new_fields}}
            response = requests.put(url, json=update_data, headers=headers)
            response.raise_for_status()
            self.logger.info(f"Zendesk Update erfolgreich: {response.status_code}")
            return True

        except Exception as e:
            self.logger.error(f"Zendesk Update Fehler: {str(e)}")
            return False

    def save_label(self, label_b64, sender_name, reference):
        """Speichert das Label als PDF-Datei im Labels Ordner."""
        try:
            # Erstelle den Labels Ordner, falls er nicht existiert
            if not os.path.exists("Labels"):
                os.makedirs("Labels")
            
            # Erstelle den Dateinamen
            filename = f"{sender_name}_{reference}.pdf"
            filepath = os.path.join("Labels", filename)
            
            # Konvertiere Base64 in Bytes
            label_bytes = base64.b64decode(label_b64)
            
            # Speichere das Label
            with open(filepath, "wb") as f:
                f.write(label_bytes)
            
            self.logger.info(f"Label gespeichert als {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des Labels: {str(e)}")
            raise


    def update_gui(self, shipment_no):
        self.log_text.append(f"Label wurde generiert. Sendungsnummer: {shipment_no}")
        #self.ref_input.setText(shipment_no)
        #QMessageBox.information(self, "Erfolg", f"Label wurde erfolgreich generiert. Sendungsnummer: {shipment_no}")



    def generate_label(self):
        """Generiert ein DHL-Label basierend auf den eingegebenen Daten."""
        try:
            # Initialisiere die DHL API
            self.initialize_dhl_api()
            
            # Sammle die Eingabedaten
            input_fields = {
                'name': self.name_input.text(),
                'street': self.street_input.text(),
                'house': self.house_input.text(),
                'postal_code': self.postal_input.text(),
                'city': self.city_input.text(),
                'email': self.email_input.text(),
                'phone': self.phone_input.text(),
                'additional_info': self.additional_info_input.text(),
                'weight': self.weight_input.text()
            }
            
            # Validiere die Eingaben
            if not validate_inputs(input_fields):
                QMessageBox.warning(self, "Fehler", "Bitte überprüfen Sie Ihre Eingaben")
                return
                
            # Erstelle die Absenderdaten
            sender_data = self.dhl_api.get_sender_data(
                name=input_fields['name'],
                street=input_fields['street'],
                house=input_fields['house'],
                postal_code=input_fields['postal_code'],
                city=input_fields['city'],
                email=input_fields['email'],
                additional_info=input_fields['additional_info'],
                phone=input_fields['phone']
            )
            
            # Hole die Referenznummer
            reference = self.ref_input.text()
            if not validate_reference_number(reference):
                QMessageBox.warning(self, "Fehler", "Die Referenznummer muss mindestens 8 Zeichen lang sein")
                return
                
            # Hole das Gewicht
            try:
                weight = float(input_fields['weight'])
            except ValueError:
                QMessageBox.warning(self, "Fehler", "Bitte geben Sie ein gültiges Gewicht ein")
                return
                
            # Generiere das Label
            # Zuerst Validierung durchführen
            _, _, validation_warning = self.dhl_api.process_label_request(
                sender_data=sender_data,
                reference=reference,
                weight=weight,
                validate=True  # Zuerst validieren
            )

            # Prüfe auf Validierungswarnungen
            if validation_warning:
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Adressvalidierung")
                msg_box.setText(f"Die Adresse konnte nicht validiert werden: {validation_warning}\n\nTrotzdem fortfahren?")
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.button(QMessageBox.Yes).setText("Ja")
                msg_box.button(QMessageBox.No).setText("Nein")
                msg_box.setDefaultButton(QMessageBox.No)
                reply = msg_box.exec_()
                if reply == QMessageBox.No:
                    return

            # Wenn Validierung erfolgreich war oder der Benutzer fortfahren möchte, Label generieren
            shipment_no, label_b64, _ = self.dhl_api.process_label_request(
                sender_data=sender_data,
                reference=reference,
                weight=weight,
                validate=False  # Jetzt das Label generieren
            )

            # Speichere das Label
            pdf_file = self.save_label(label_b64, self.name_input.text().strip(), reference)
            self.update_gui(shipment_no)

            # Aktualisiere die Zendesk Felder
            ticket_id = self.ticket_nr_input.text().strip()
            if ticket_id:
                # Hole die ausgewählte Bestellung
                order_index = self.orders_dropdown.currentIndex()
                if order_index > 0:  # Wenn eine Bestellung ausgewählt ist
                    selected_order = self.orders_dropdown.itemData(order_index)
                    if selected_order:
                        # Extrahiere die Seriennummer aus den Notizen
                        notes = selected_order.get("SellerComment", "")
                        if notes:
                            serial_number = self.bb_api.extract_serial_number(notes)
                            if serial_number:
                                # Aktualisiere das Seriennummer-Feld im Zendesk-Ticket
                                if update_serial_number(ticket_id, self.zendesk_email, self.zendesk_token, serial_number):
                                    self.logger.info(f"Seriennummer {serial_number} zu Zendesk-Ticket {ticket_id} hinzugefügt")
                                else:
                                    self.logger.info("Fehler beim Aktualisieren der Seriennummer im Zendesk-Ticket")

                        # Hole Bestellnummer und -datum
                        order_number = selected_order.get("OrderNumber", "")
                        order_date = selected_order.get("CreatedAt", "")  # Verwende CreatedAt statt Created
                        if order_date:
                            # Konvertiere das Datum in ein lesbares Format
                            try:
                                order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00')).strftime('%d.%m.%Y')
                            except:
                                order_date = order_date.split('T')[0]  # Fallback: Nur das Datum ohne Zeit

                        # Erstelle den Bestelltext
                        order_text = f"Bestellnummer: {order_number}"
                        if order_date:
                            order_text += f" vom {order_date}"

                        # Aktualisiere das Bestellfeld im Zendesk-Ticket
                        if update_order_info(ticket_id, self.zendesk_email, self.zendesk_token, order_text):
                            self.logger.info(f"Bestellinformationen zu Zendesk-Ticket {ticket_id} hinzugefügt")
                        else:
                            self.logger.info("Fehler beim Aktualisieren der Bestellinformationen im Zendesk-Ticket")

                fields_update = {
                    18851720152732: shipment_no,  # Trackingnummer
                    7566313720220: self.name_input.text().strip()    # Bestellname
                }
                if self.update_zendesk_ticket_fields(ticket_id, fields_update):
                    self.logger.info(
                        f"Sendungsnr {shipment_no} und Bestellname '{self.name_input.text().strip()}' zu Zendesk-Ticket {ticket_id} hinzugefügt"
                    )
                else:
                    self.logger.info("Fehler beim Aktualisieren des Zendesk-Tickets")

            # Zeige Erfolgsmeldung
            success_message = f"Label erfolgreich erstellt!\nSendungsnummer: {shipment_no}"
            if validation_warning:
                success_message += f"\n\n{validation_warning}"
            QMessageBox.information(self, "Erfolg", success_message)

            # Lösche die Felder wenn auto clear aktiviert ist
            if self.clear_fields_checkbox.isChecked():
                utils.clear_all_fields(self)

        except Exception as e:
            self.logger.error(f"Fehler bei der Label-Generierung: {str(e)}")
            QMessageBox.critical(self, "Fehler", str(e))

    def on_clear_fields_changed(self, state):
        # Implementiere die Logik, wenn sich die Checkbox "Felder automatisch leeren" ändert
        pass

    def load_api_credentials(self, master_password):
        """Lädt die API-Credentials aus der Keepass-Datei."""
        try:
            from keepass import load_credentials
            credentials = load_credentials(master_password)
            
            # DHL Credentials
            self.username = credentials.get('dhl_username')
            self.password = credentials.get('dhl_password')
            self.client_id = credentials.get('dhl_client_id')
            self.client_secret = credentials.get('dhl_client_secret')
            self.billing_number = credentials.get('dhl_billing_number')
            
            # Zendesk Credentials
            self.zendesk_email = credentials.get('zendesk_email')
            self.zendesk_token = credentials.get('zendesk_token')
            
            # Billbee Credentials
            self.bb_api_key = credentials.get('billbee_api_key')
            self.bb_api_user = credentials.get('billbee_api_user')
            self.bb_api_password = credentials.get('billbee_api_password')
            
            self.logger.info("API-Credentials erfolgreich geladen")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der API-Credentials: {str(e)}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der API-Credentials: {str(e)}")

    def extract_and_update_serial(self):
        """Extrahiert die Seriennummer aus den Notizen und zeigt sie im Problembeschreibungsfeld an."""
        try:
            # Prüfe, ob eine Bestellung ausgewählt wurde
            order_index = self.orders_dropdown.currentIndex()
            if order_index <= 0:  # 0 ist der Platzhalter
                QMessageBox.warning(self, "Fehler", "Bitte eine Bestellung auswählen")
                return

            selected_order = self.orders_dropdown.itemData(order_index)
            if not selected_order:
                QMessageBox.warning(self, "Fehler", "Keine gültige Bestellung ausgewählt")
                return

            # Initialisiere die Billbee-API
            if not hasattr(self, 'bb_api') or self.bb_api is None:
                self.bb_api = BillbeeAPI(
                    api_key=self.bb_api_key,
                    api_user=self.bb_api_user,
                    api_password=self.bb_api_password
                )

            # Hole die Notizen der ausgewählten Bestellung
            notes = self.bb_api.get_order_notes(selected_order["Id"])
            if not notes:
                QMessageBox.warning(self, "Fehler", "Keine Notizen für die ausgewählte Bestellung gefunden")
                return

            # Zeige die Notizen an
            self.log_text.append(f"\nNotizen für Bestellung {selected_order.get('OrderNumber', 'Unbekannt')}:")
            self.log_text.append("-" * 50)
            self.log_text.append(notes)
            self.log_text.append("-" * 50)

            # Extrahiere die Seriennummer
            serial_number = self.bb_api.extract_serial_number(notes)
            if serial_number:
                # Setze die Seriennummer in das Problembeschreibungsfeld
                self.problem_description.setText(f"Seriennummer: {serial_number}")
                self.logger.info(f"\nSeriennummer gefunden: {serial_number}")
            else:
                self.logger.info("\nKeine Seriennummer in den Notizen gefunden")

        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Notizen: {str(e)}")
            QMessageBox.critical(self, "Fehler", str(e))

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        
        # Lade das Styling
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        style_path = os.path.join(base_dir, "global_style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding='utf-8') as f:
                app.setStyleSheet(f.read())
        
        # Erstelle und zeige das Hauptfenster
        window = DHLLabelGenerator()
        
        # Frage nach dem Master-Passwort
        password, ok = QInputDialog.getText(
            window, 
            "Master-Passwort",
            "Bitte geben Sie das Master-Passwort ein:",
            QLineEdit.Password
        )
        
        if ok:
            # Lade die API-Credentials
            window.load_api_credentials(password)
            window.show()
            sys.exit(app.exec_())
        else:
            sys.exit(0)
            
    except Exception as e:
        # Wenn ein Fehler auftritt, versuche ihn zu loggen
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            log_dir = os.path.join(base_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            error_log_path = os.path.join(log_dir, "startup_error.log")
            with open(error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n\n=== Startup Error {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.write(str(e))
                f.write("\n")
                f.write(traceback.format_exc())
        except:
            pass  # Wenn selbst das Logging fehlschlägt, können wir nichts mehr tun
        
        # Zeige eine Fehlermeldung an
        if 'app' in locals():
            QMessageBox.critical(None, "Kritischer Fehler", f"Fehler beim Starten der Anwendung:\n\n{str(e)}")
        sys.exit(1)
