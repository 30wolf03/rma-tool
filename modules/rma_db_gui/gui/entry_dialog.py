"""Dialog für das Erstellen und Bearbeiten von RMA-Einträgen."""

from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QPushButton,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QDateEdit,
    QCheckBox,
    QSpinBox
)

from loguru import logger
from ..database.connection import DatabaseConnection


class EntryDialog(QDialog):
    """Dialog für das Erstellen und Bearbeiten von RMA-Einträgen."""

    def __init__(
        self,
        parent=None,
        db_connection: Optional[DatabaseConnection] = None,
        ticket_number: Optional[str] = None,
        is_edit_mode: bool = False
    ) -> None:
        """Initialisiert den Eintrag-Dialog.
        
        Args:
            parent: Parent-Widget
            db_connection: Datenbankverbindung
            ticket_number: Ticket-Nummer für Bearbeitungsmodus
            is_edit_mode: True für Bearbeitung, False für Erstellung
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.ticket_number = ticket_number
        self.is_edit_mode = is_edit_mode
        
        # Cache für Dropdown-Daten
        self.handlers = []
        self.storage_locations = []
        
        self.setWindowTitle("RMA-Eintrag bearbeiten" if is_edit_mode else "Neuen RMA-Eintrag erstellen")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        
        self._setup_ui()
        self._load_dropdown_data()
        
        if is_edit_mode and ticket_number:
            self._load_existing_data()

    def _setup_ui(self) -> None:
        """Richtet die Benutzeroberfläche ein."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Formular-Layout
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Ticket Number (manuell eingeben für Zendesk-Zuordnung)
        self.ticket_number_input = QLineEdit()
        if self.is_edit_mode:
            self.ticket_number_input.setReadOnly(True)
        else:
            self.ticket_number_input.setPlaceholderText("Zendesk Ticket-Nummer eingeben")
        form_layout.addRow("Ticket-Nummer:", self.ticket_number_input)
        
        # Order Number
        self.order_number_input = QLineEdit()
        form_layout.addRow("Auftragsnummer:", self.order_number_input)
        
        # Type
        self.type_input = QComboBox()
        self.type_input.addItems(["Reparatur", "Widerruf", "Ersatz", "Rückerstattung", "Sonstiges"])
        self.type_input.setEditable(True)
        form_layout.addRow("Typ:", self.type_input)
        
        # Entry Date
        self.entry_date_input = QDateEdit()
        self.entry_date_input.setDate(datetime.now().date())
        self.entry_date_input.setCalendarPopup(True)
        form_layout.addRow("Eingangsdatum:", self.entry_date_input)
        
        # Status
        self.status_input = QComboBox()
        self.status_input.addItems(["Open", "In Progress", "Completed", "Closed"])
        form_layout.addRow("Status:", self.status_input)
        
        # Exit Date
        self.exit_date_input = QDateEdit()
        self.exit_date_input.setCalendarPopup(True)
        self.exit_date_input.setDate(datetime.now().date())
        form_layout.addRow("Ausgangsdatum:", self.exit_date_input)
        
        # Tracking Number
        self.tracking_number_input = QLineEdit()
        form_layout.addRow("Tracking-Nummer:", self.tracking_number_input)
        
        # Is Amazon
        self.is_amazon_input = QCheckBox()
        form_layout.addRow("Amazon-Bestellung:", self.is_amazon_input)
        
        # Storage Location (Dropdown)
        self.storage_location_input = QComboBox()
        form_layout.addRow("Lagerort:", self.storage_location_input)
        
        # Last Handler (Dropdown)
        self.last_handler_input = QComboBox()
        form_layout.addRow("Letzter Bearbeiter:", self.last_handler_input)
        
        # Product Information
        product_label = QLabel("Produkt-Informationen:")
        product_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        form_layout.addRow(product_label)
        
        self.product_name_input = QLineEdit()
        form_layout.addRow("Produktname:", self.product_name_input)
        
        self.serial_number_input = QLineEdit()
        form_layout.addRow("Seriennummer:", self.serial_number_input)
        
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999)
        self.quantity_input.setValue(1)
        form_layout.addRow("Menge:", self.quantity_input)
        
        # Repair Details
        repair_label = QLabel("Reparatur-Details:")
        repair_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        form_layout.addRow(repair_label)
        
        self.customer_description_input = QTextEdit()
        self.customer_description_input.setMaximumHeight(80)
        form_layout.addRow("Kundenbeschreibung:", self.customer_description_input)
        
        self.problem_cause_input = QTextEdit()
        self.problem_cause_input.setMaximumHeight(80)
        form_layout.addRow("Problemursache:", self.problem_cause_input)
        
        self.last_action_input = QTextEdit()
        self.last_action_input.setMaximumHeight(80)
        form_layout.addRow("Letzte Aktion:", self.last_action_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_dropdown_data(self) -> None:
        """Lädt die Daten für die Dropdown-Menüs."""
        if not self.db_connection:
            return
            
        try:
            # Lade Handlers
            handlers_query = "SELECT Initials, Name FROM Handlers ORDER BY Name"
            handlers_result = self.db_connection.execute_query(handlers_query)
            self.handlers = [(row['Initials'], f"{row['Name']} ({row['Initials']})") 
                           for row in handlers_result] if handlers_result else []
            
            # Lade Storage Locations
            locations_query = "SELECT ID, LocationName FROM StorageLocations ORDER BY LocationName"
            locations_result = self.db_connection.execute_query(locations_query)
            self.storage_locations = [(row['ID'], row['LocationName']) 
                                    for row in locations_result] if locations_result else []
            
            # Fülle Dropdowns
            self.last_handler_input.clear()
            self.last_handler_input.addItem("", "")
            for initials, display_name in self.handlers:
                self.last_handler_input.addItem(display_name, initials)
            
            self.storage_location_input.clear()
            self.storage_location_input.addItem("", "")
            for location_id, location_name in self.storage_locations:
                self.storage_location_input.addItem(location_name, location_id)
                
        except Exception as e:
            logger.error(f"Fehler beim Laden der Dropdown-Daten: {e}")

    def _convert_type_to_db(self, display_text: str) -> str:
        """Konvertiert deutschen Type-Text zu englischem Datenbankwert."""
        type_mapping = {
            'Reparatur': 'repair',
            'Widerruf': 'return',
            'Ersatz': 'replace',
            'Rückerstattung': 'refund',
            'Sonstiges': 'other'
        }
        return type_mapping.get(display_text, display_text)

    def _load_existing_data(self) -> None:
        """Lädt existierende Daten für den Bearbeitungsmodus."""
        if not self.db_connection or not self.ticket_number:
            return
            
        try:
            # Lade RMA_Cases Daten
            cases_query = """
                SELECT c.*, s.LocationName
                FROM RMA_Cases c
                LEFT JOIN StorageLocations s ON c.StorageLocationID = s.ID
                WHERE c.TicketNumber = %s
            """
            cases_result = self.db_connection.execute_query(cases_query, (self.ticket_number,))
            
            if cases_result:
                case_data = cases_result[0]
                
                # Fülle Formular mit existierenden Daten
                self.ticket_number_input.setText(case_data.get('TicketNumber', ''))
                self.order_number_input.setText(case_data.get('OrderNumber', ''))
                
                # Type
                type_text = case_data.get('Type', '')
                # Type-Mapping: Englische Werte -> Deutsche Anzeige
                type_mapping = {
                    'repair': 'Reparatur',
                    'return': 'Widerruf',
                    'replace': 'Ersatz',
                    'refund': 'Rückerstattung',
                    'other': 'Sonstiges'
                }
                display_text = type_mapping.get(type_text, type_text)
                index = self.type_input.findText(display_text)
                if index >= 0:
                    self.type_input.setCurrentIndex(index)
                else:
                    self.type_input.setCurrentText(display_text)
                
                # Dates
                if case_data.get('EntryDate'):
                    self.entry_date_input.setDate(case_data['EntryDate'])
                if case_data.get('ExitDate'):
                    self.exit_date_input.setDate(case_data['ExitDate'])
                
                # Status
                status_text = case_data.get('Status', '')
                index = self.status_input.findText(status_text)
                if index >= 0:
                    self.status_input.setCurrentIndex(index)
                
                self.tracking_number_input.setText(case_data.get('TrackingNumber', ''))
                self.is_amazon_input.setChecked(case_data.get('IsAmazon', False))
                
                # Storage Location
                storage_id = case_data.get('StorageLocationID')
                if storage_id:
                    index = self.storage_location_input.findData(storage_id)
                    if index >= 0:
                        self.storage_location_input.setCurrentIndex(index)
            
            # Lade RMA_Products Daten
            products_query = """
                SELECT * FROM RMA_Products 
                WHERE TicketNumber = %s AND IsDeleted = FALSE
            """
            products_result = self.db_connection.execute_query(products_query, (self.ticket_number,))
            
            if products_result:
                product_data = products_result[0]
                self.product_name_input.setText(product_data.get('ProductName', ''))
                self.serial_number_input.setText(product_data.get('SerialNumber', ''))
                self.quantity_input.setValue(product_data.get('Quantity', 1))
            
            # Lade RMA_RepairDetails Daten
            repair_query = """
                SELECT * FROM RMA_RepairDetails 
                WHERE TicketNumber = %s AND IsDeleted = FALSE
            """
            repair_result = self.db_connection.execute_query(repair_query, (self.ticket_number,))
            
            if repair_result:
                repair_data = repair_result[0]
                self.customer_description_input.setText(repair_data.get('CustomerDescription', ''))
                self.problem_cause_input.setText(repair_data.get('ProblemCause', ''))
                self.last_action_input.setText(repair_data.get('LastAction', ''))
                
                # Last Handler
                last_handler = repair_data.get('LastHandler')
                if last_handler:
                    index = self.last_handler_input.findData(last_handler)
                    if index >= 0:
                        self.last_handler_input.setCurrentIndex(index)
                        
        except Exception as e:
            logger.error(f"Fehler beim Laden der existierenden Daten: {e}")

    def _accept(self) -> None:
        """Behandelt das Akzeptieren des Dialogs."""
        if not self._validate_input():
            return
            
        try:
            if self.is_edit_mode:
                self._update_existing_entry()
            else:
                self._create_new_entry()
                
            self.accept()
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Eintrags: {e}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {e}")

    def _validate_input(self) -> bool:
        """Validiert die Eingaben."""
        if not self.ticket_number_input.text().strip():
            QMessageBox.warning(self, "Validierung", "Ticket-Nummer ist erforderlich.")
            return False
            
        if not self.order_number_input.text().strip():
            QMessageBox.warning(self, "Validierung", "Auftragsnummer ist erforderlich.")
            return False
            
        return True

    def _create_new_entry(self) -> None:
        """Erstellt einen neuen RMA-Eintrag."""
        if not self.db_connection:
            raise Exception("Keine Datenbankverbindung")
            
        ticket_number = self.ticket_number_input.text().strip()
        order_number = self.order_number_input.text().strip()
        
        with self.db_connection.get_connection() as conn:
            cursor = conn.cursor()
            
            # Beginne Transaktion
            cursor.execute("START TRANSACTION")
            
            try:
                # Erstelle RMA_Cases Eintrag
                cursor.execute("""
                    INSERT INTO RMA_Cases (
                        TicketNumber, OrderNumber, Type, EntryDate, Status, 
                        ExitDate, TrackingNumber, IsAmazon, StorageLocationID
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticket_number,
                    order_number,
                    self._convert_type_to_db(self.type_input.currentText()),
                    self.entry_date_input.date().toPython(),
                    self.status_input.currentText(),
                    self.exit_date_input.date().toPython(),
                    self.tracking_number_input.text().strip(),
                    self.is_amazon_input.isChecked(),
                    self.storage_location_input.currentData() or None
                ))
                
                # Erstelle RMA_Products Eintrag
                cursor.execute("""
                    INSERT INTO RMA_Products (
                        TicketNumber, OrderNumber, ProductName, SerialNumber, Quantity
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    ticket_number,
                    order_number,
                    self.product_name_input.text().strip(),
                    self.serial_number_input.text().strip(),
                    self.quantity_input.value()
                ))
                
                # Erstelle RMA_RepairDetails Eintrag
                cursor.execute("""
                    INSERT INTO RMA_RepairDetails (
                        TicketNumber, OrderNumber, CustomerDescription, 
                        ProblemCause, LastAction, LastHandler
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    ticket_number,
                    order_number,
                    self.customer_description_input.toPlainText().strip(),
                    self.problem_cause_input.toPlainText().strip(),
                    self.last_action_input.toPlainText().strip(),
                    self.last_handler_input.currentData() or None
                ))
                
                # Commit Transaktion
                cursor.execute("COMMIT")
                logger.info(f"Neuer RMA-Eintrag erstellt: {ticket_number}")
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e

    def _update_existing_entry(self) -> None:
        """Aktualisiert einen existierenden RMA-Eintrag."""
        if not self.db_connection or not self.ticket_number:
            raise Exception("Keine Datenbankverbindung oder Ticket-Nummer")
            
        with self.db_connection.get_connection() as conn:
            cursor = conn.cursor()
            
            # Beginne Transaktion
            cursor.execute("START TRANSACTION")
            
            try:
                # Aktualisiere RMA_Cases
                cursor.execute("""
                    UPDATE RMA_Cases SET
                        OrderNumber = %s, Type = %s, EntryDate = %s, Status = %s,
                        ExitDate = %s, TrackingNumber = %s, IsAmazon = %s, 
                        StorageLocationID = %s
                    WHERE TicketNumber = %s
                """, (
                    self.order_number_input.text().strip(),
                    self._convert_type_to_db(self.type_input.currentText()),
                    self.entry_date_input.date().toPython(),
                    self.status_input.currentText(),
                    self.exit_date_input.date().toPython(),
                    self.tracking_number_input.text().strip(),
                    self.is_amazon_input.isChecked(),
                    self.storage_location_input.currentData() or None,
                    self.ticket_number
                ))
                
                # Aktualisiere RMA_Products
                cursor.execute("""
                    UPDATE RMA_Products SET
                        OrderNumber = %s, ProductName = %s, SerialNumber = %s, 
                        Quantity = %s
                    WHERE TicketNumber = %s AND IsDeleted = FALSE
                """, (
                    self.order_number_input.text().strip(),
                    self.product_name_input.text().strip(),
                    self.serial_number_input.text().strip(),
                    self.quantity_input.value(),
                    self.ticket_number
                ))
                
                # Aktualisiere RMA_RepairDetails
                cursor.execute("""
                    UPDATE RMA_RepairDetails SET
                        OrderNumber = %s, CustomerDescription = %s, 
                        ProblemCause = %s, LastAction = %s, LastHandler = %s
                    WHERE TicketNumber = %s AND IsDeleted = FALSE
                """, (
                    self.order_number_input.text().strip(),
                    self.customer_description_input.toPlainText().strip(),
                    self.problem_cause_input.toPlainText().strip(),
                    self.last_action_input.toPlainText().strip(),
                    self.last_handler_input.currentData() or None,
                    self.ticket_number
                ))
                
                # Commit Transaktion
                cursor.execute("COMMIT")
                logger.info(f"RMA-Eintrag aktualisiert: {self.ticket_number}")
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e 