"""Main window for the RMA Database GUI.

This module provides the main application window with a modern, user-friendly
interface for managing RMA database entries.
"""

from __future__ import annotations

import sys
from typing import Optional, List
from datetime import datetime

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QPushButton,
    QLineEdit,
    QLabel,
    QStatusBar,
    QHeaderView,
    QStyle,
    QToolBar,
    QMenu,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QTextEdit,
    QCheckBox,
)

from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog

from loguru import logger

from ..config.settings import (
    WINDOW_TITLE,
    WINDOW_SIZE,
    LOG_LEVEL,
    LOG_FORMAT,
    get_log_file,
)
from ..database.connection import DatabaseConnection, DatabaseConnectionError
from ..utils.keepass_handler import KeepassHandler, KeepassError
from .dialogs import DeleteConfirmationDialog
from .login_window import LoginDialog
from .entry_dialog import EntryDialog

# Import the credential cache
from shared.credentials.credential_cache import get_credential_cache
from shared.credentials.keepass_handler import CentralKeePassHandler

# Configure logging
logger.remove()  # Remove default handler

# Log in die Konsole
logger.add(sys.stderr, level=LOG_LEVEL, format=LOG_FORMAT)

# Log in die Datei
logger.add(str(get_log_file()), level=LOG_LEVEL, format=LOG_FORMAT, encoding="utf-8")



class MainWindow(QMainWindow):
    """Main window for the RMA Database GUI.

    This class provides a modern, user-friendly interface for managing
    RMA database entries with proper error handling and status feedback.
    """

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.credential_cache = get_credential_cache()
        # Hole zentralen Handler aus Cache
        self.central_kp_handler = self.credential_cache.get_keepass_handler()
        if not self.central_kp_handler or not self.central_kp_handler.is_database_open():
            LoggingMessageBox.critical(
                self, 
                "Fehler", 
                "Keine zentrale Authentifizierung gefunden. Bitte Anwendung neu starten."
            )
            sys.exit(1)
        
        # Papierkorb-Status
        self.show_deleted_entries = False
        self.current_user = "MWO"  # Wird später aus dem Login gesetzt
        
        self._setup_ui()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_connections()
        try:
            self.db_connection = DatabaseConnection(self.central_kp_handler)
            self.load_rma_data()
        except Exception as e:
            self._show_error("Verbindungsfehler", str(e))
            sys.exit(1)

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        # Window setup
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(QSize(800, 600))

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Password input section
        password_widget = QWidget()
        password_layout = QHBoxLayout(password_widget)
        password_layout.setContentsMargins(0, 0, 0, 0)

        # Password label
        password_label = QLabel("KeePass Master Password:")
        password_label.setFont(QFont("Segoe UI", 10))
        password_layout.addWidget(password_label)

        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFont(QFont("Segoe UI", 10))
        self.password_input.setPlaceholderText("Enter KeePass master password")
        password_layout.addWidget(self.password_input)

        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.setFont(QFont("Segoe UI", 10))
        password_layout.addWidget(self.connect_button)

        main_layout.addWidget(password_widget)

        # Create table
        self.table = QTableWidget()
        self.table.setFont(QFont("Segoe UI", 9))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Deaktiviere die Standard-Sortierung, da wir unsere eigene verwenden
        self.table.setSortingEnabled(False)
        
        # Setze Header-Eigenschaften für bessere Sortierung
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setStretchLastSection(True)
        
        main_layout.addWidget(self.table)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _setup_toolbar(self) -> None:
        """Set up the toolbar with action buttons."""
        toolbar = QToolBar("Hauptwerkzeugleiste")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Delete action
        self.delete_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            "Löschen",
            self
        )
        self.delete_action.setStatusTip("Ausgewählte RMA-Einträge löschen")
        self.delete_action.triggered.connect(self._delete_selected_entries)
        toolbar.addAction(self.delete_action)

        # Refresh action
        refresh_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            "Aktualisieren",
            self
        )
        refresh_action.setStatusTip("RMA-Daten aktualisieren")
        refresh_action.triggered.connect(self.load_rma_data)
        toolbar.addAction(refresh_action)

        # Neuen Eintrag erstellen
        add_new_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Neuen Eintrag erstellen",
            self
        )
        add_new_action.setStatusTip("Erstellt einen neuen RMA-Eintrag")
        add_new_action.triggered.connect(self._create_new_entry)
        toolbar.addAction(add_new_action)

        # Testeintrag anlegen
        add_test_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Testeintrag anlegen",
            self
        )
        add_test_action.setStatusTip("Fügt einen Dummy-RMA-Eintrag zum Testen hinzu")
        add_test_action.triggered.connect(self._add_test_entry)
        toolbar.addAction(add_test_action)

        # Papierkorb-Toggle
        self.trash_toggle_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            "Papierkorb anzeigen",
            self
        )
        self.trash_toggle_action.setStatusTip("Wechselt zwischen aktiven Einträgen und Papierkorb")
        self.trash_toggle_action.triggered.connect(self._toggle_trash_view)
        self.trash_toggle_action.setCheckable(True)
        toolbar.addAction(self.trash_toggle_action)

        # Wiederherstellen (nur sichtbar im Papierkorb)
        self.restore_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp),
            "Wiederherstellen",
            self
        )
        self.restore_action.setStatusTip("Ausgewählte Einträge aus dem Papierkorb wiederherstellen")
        self.restore_action.triggered.connect(self._restore_selected_entries)
        self.restore_action.setVisible(False)
        toolbar.addAction(self.restore_action)

        # Context menu for table
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Verbinde Tabellen-Änderungen
        self.table.itemChanged.connect(self._on_table_item_changed)
        
        # Verbinde Doppelklick für Dropdown-Spalten
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def _show_context_menu(self, position) -> None:
        """Zeigt das Kontextmenü für die Tabelle an."""
        menu = QMenu()
        
        if self.show_deleted_entries:
            # Im Papierkorb: Wiederherstellen anzeigen
            restore_action = menu.addAction("Wiederherstellen")
            restore_action.triggered.connect(self._restore_selected_entries)
            
            menu.addSeparator()
            
            # Endgültig löschen (nur für Admins oder nach Bestätigung)
            permanent_delete_action = menu.addAction("Endgültig löschen")
            permanent_delete_action.triggered.connect(self._permanent_delete_selected_entries)
        else:
            # Bei aktiven Einträgen: Bearbeiten und Löschen anzeigen
            edit_action = menu.addAction("Bearbeiten")
            edit_action.triggered.connect(self._edit_selected_entry)
            
            menu.addSeparator()
            
            delete_action = menu.addAction("Löschen")
            delete_action.triggered.connect(self._delete_selected_entries)
        
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _get_selected_rma_numbers(self) -> List[str]:
        """Gibt die RMA-Nummern der ausgewählten Einträge zurück."""
        selected_rows = set(item.row() for item in self.table.selectedItems())
        rma_numbers = []
        
        for row in selected_rows:
            rma_item = self.table.item(row, self.table.horizontalHeader().logicalIndex(0))
            if rma_item:
                rma_numbers.append(rma_item.text())
        
        return rma_numbers

    def _delete_selected_entries(self) -> None:
        """Führt ein Soft Delete für die ausgewählten RMA-Einträge durch."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return

        rma_numbers = self._get_selected_rma_numbers()
        logger.info(f"Archivierung angefordert für {len(rma_numbers)} Einträge: {rma_numbers}")
        
        if not rma_numbers:
            self._show_error("Fehler", "Bitte wählen Sie mindestens einen Eintrag aus")
            return

        # Bestätigungsdialog anzeigen
        dialog = DeleteConfirmationDialog(self, rma_numbers)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            logger.info("Archivierung vom Benutzer abgebrochen")
            return

        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Beginne Transaktion
                cursor.execute("START TRANSACTION")
                logger.info("Datenbank-Transaktion gestartet")
                
                try:
                    # Soft Delete für RMA_Cases
                    logger.info(f"Führe Soft Delete für RMA_Cases durch - {len(rma_numbers)} Einträge")
                    cursor.execute(
                        """
                        UPDATE RMA_Cases 
                        SET IsDeleted = TRUE, 
                            DeletedAt = CURRENT_TIMESTAMP,
                            DeletedBy = %s
                        WHERE TicketNumber IN %s
                        """,
                        (self.current_user, rma_numbers)
                    )
                    cases_updated = cursor.rowcount
                    logger.info(f"RMA_Cases aktualisiert: {cases_updated} Zeilen betroffen")
                    
                    # Soft Delete für zugehörige Daten
                    logger.info("Führe Soft Delete für RMA_RepairDetails durch")
                    cursor.execute(
                        """
                        UPDATE RMA_RepairDetails 
                        SET IsDeleted = TRUE,
                            DeletedAt = CURRENT_TIMESTAMP,
                            DeletedBy = %s
                        WHERE TicketNumber IN %s
                        """,
                        (self.current_user, rma_numbers)
                    )
                    repair_details_updated = cursor.rowcount
                    logger.info(f"RMA_RepairDetails aktualisiert: {repair_details_updated} Zeilen betroffen")
                    
                    logger.info("Führe Soft Delete für RMA_Products durch")
                    cursor.execute(
                        """
                        UPDATE RMA_Products 
                        SET IsDeleted = TRUE,
                            DeletedAt = CURRENT_TIMESTAMP,
                            DeletedBy = %s
                        WHERE TicketNumber IN %s
                        """,
                        (self.current_user, rma_numbers)
                    )
                    products_updated = cursor.rowcount
                    logger.info(f"RMA_Products aktualisiert: {products_updated} Zeilen betroffen")
                    
                    # Commit Transaktion
                    cursor.execute("COMMIT")
                    logger.info("Datenbank-Transaktion erfolgreich committed")
                    
                    self._show_success(
                        "Erfolg",
                        f"{len(rma_numbers)} RMA-Einträge wurden archiviert"
                    )
                    
                    # Tabelle aktualisieren
                    logger.info("Lade RMA-Daten neu nach Archivierung")
                    self.load_rma_data()
                    
                except Exception as e:
                    # Bei Fehler Rollback
                    cursor.execute("ROLLBACK")
                    logger.error(f"Fehler während Archivierung - Rollback durchgeführt: {e}")
                    raise e
                    
        except DatabaseConnectionError as e:
            logger.error(f"Datenbankverbindungsfehler beim Archivieren: {e}")
            self._show_error("Datenbankfehler", str(e))
        except Exception as e:
            logger.exception("Fehler beim Archivieren der Einträge")
            self._show_error("Fehler", f"Unerwarteter Fehler: {e}")

    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setFont(QFont("Segoe UI", 9))
        self.status_bar.showMessage("Ready")

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.connect_button.clicked.connect(self.connect_to_database)
        self.password_input.returnPressed.connect(self.connect_to_database)
        
        # Verbinde Header-Sortierung mit unserer benutzerdefinierten Sortier-Methode
        header = self.table.horizontalHeader()
        header.sectionClicked.connect(self._handle_sort)

    def _show_error(self, title: str, message: str) -> None:
        """Show an error message dialog.

        Args:
            title: The dialog title.
            message: The error message to display.
        """
        LoggingMessageBox.critical(self, title, message)
        self.status_bar.showMessage(f"Error: {message}", 5000)

    def _show_success(self, title: str, message: str) -> None:
        """Show a success message dialog.

        Args:
            title: The dialog title.
            message: The success message to display.
        """
        LoggingMessageBox.information(self, title, message)
        self.status_bar.showMessage(message, 5000)

    def connect_to_database(self) -> None:
        """Connect to the database using KeePass credentials."""
        password = self.password_input.text()
        if not password:
            self._show_error("Input Error", "Please enter the KeePass master password")
            return

        try:
            # Create KeepassHandler and DatabaseConnection
            keepass_handler = KeepassHandler(password)
            self.db_connection = DatabaseConnection(keepass_handler)

            # Test connection with a simple query
            results = self.db_connection.execute_query("SELECT 1")
            if results:
                self._show_success("Success", "Successfully connected to the database!")
                self.load_rma_data()
                self.password_input.clear()
                self.password_input.setEnabled(False)
                self.connect_button.setEnabled(False)
            else:
                raise DatabaseConnectionError("Query returned no results")

        except KeepassError as e:
            self._show_error("KeePass Error", str(e))
        except DatabaseConnectionError as e:
            self._show_error("Connection Error", str(e))
        except Exception as e:
            logger.exception("Unexpected error during database connection")
            self._show_error("Error", f"An unexpected error occurred: {e}")



    def load_rma_data(self) -> None:
        """Load RMA data from the database and display it in the table."""
        if not self.db_connection:
            logger.warning("Keine Datenbankverbindung verfügbar für load_rma_data")
            return

        try:
            logger.info("Starte load_rma_data - Lade Daten aus der Datenbank")
            
            # Speichere aktuelle Sortierreihenfolge
            header = self.table.horizontalHeader()
            current_sort_column = header.sortIndicatorSection()
            current_sort_order = header.sortIndicatorOrder()
            logger.info(f"Aktuelle Sortierung - Spalte: {current_sort_column}, Richtung: {current_sort_order}")
            
            # Execute query to get RMA data with storage location names and handler
            if self.show_deleted_entries:
                # Papierkorb-Ansicht: Zeige gelöschte Einträge
                query = """
                    SELECT 
                        c.TicketNumber,
                        c.OrderNumber,
                        c.Type,
                        c.EntryDate,
                        c.Status,
                        c.ExitDate,
                        c.TrackingNumber,
                        c.IsAmazon,
                        s.LocationName as StorageLocation,
                        rd.LastHandler,
                        h.Name as HandlerName,
                        c.IsDeleted,
                        c.DeletedAt,
                        c.DeletedBy
                    FROM RMA_Cases c
                    LEFT JOIN StorageLocations s ON c.StorageLocationID = s.ID
                    LEFT JOIN RMA_RepairDetails rd ON c.TicketNumber = rd.TicketNumber AND rd.IsDeleted = TRUE
                    LEFT JOIN Handlers h ON rd.LastHandler = h.Initials
                    WHERE c.IsDeleted = TRUE
                    ORDER BY c.DeletedAt DESC
                """
            else:
                # Normale Ansicht: Zeige aktive Einträge
                query = """
                    SELECT 
                        c.TicketNumber,
                        c.OrderNumber,
                        c.Type,
                        c.EntryDate,
                        c.Status,
                        c.ExitDate,
                        c.TrackingNumber,
                        c.IsAmazon,
                        s.LocationName as StorageLocation,
                        rd.LastHandler,
                        h.Name as HandlerName,
                        c.IsDeleted,
                        c.DeletedAt,
                        c.DeletedBy
                    FROM RMA_Cases c
                    LEFT JOIN StorageLocations s ON c.StorageLocationID = s.ID
                    LEFT JOIN RMA_RepairDetails rd ON c.TicketNumber = rd.TicketNumber AND rd.IsDeleted = FALSE
                    LEFT JOIN Handlers h ON rd.LastHandler = h.Initials
                    WHERE c.IsDeleted = FALSE
                    ORDER BY c.TicketNumber DESC
                """
            logger.info("Führe Datenbankabfrage aus")
            results = self.db_connection.execute_query(query)
            logger.info(f"Datenbankabfrage abgeschlossen - {len(results) if results else 0} Ergebnisse erhalten")

            if not results:
                logger.info("Keine RMA-Daten gefunden - Tabelle wird geleert")
                self.table.setRowCount(0)
                self.status_bar.showMessage("No RMA data found", 5000)
                return

            # Set up table
            # Zeige Spalten basierend auf Ansicht
            if self.show_deleted_entries:
                # Papierkorb-Ansicht: Zusätzliche Spalten für gelöschte Einträge
                visible_columns = [
                    'TicketNumber', 'OrderNumber', 'Type', 'EntryDate', 
                    'Status', 'ExitDate', 'TrackingNumber', 'IsAmazon',
                    'StorageLocation', 'LastHandler', 'DeletedAt', 'DeletedBy'
                ]
            else:
                # Normale Ansicht: Standard-Spalten
                visible_columns = [
                    'TicketNumber', 'OrderNumber', 'Type', 'EntryDate', 
                    'Status', 'ExitDate', 'TrackingNumber', 'IsAmazon',
                    'StorageLocation', 'LastHandler'
                ]
            logger.info(f"Richte Tabelle ein - {len(results)} Zeilen, {len(visible_columns)} Spalten")
            self.table.setRowCount(len(results))
            self.table.setColumnCount(len(visible_columns))
            
            # Setze die Spaltenüberschriften
            headers = []
            for col in visible_columns:
                if col == 'HandlerName':
                    headers.append('LastHandler')
                elif col == 'DeletedAt':
                    headers.append('Gelöscht am')
                elif col == 'DeletedBy':
                    headers.append('Gelöscht von')
                else:
                    headers.append(col)
            self.table.setHorizontalHeaderLabels(headers)
            logger.info(f"Spaltenüberschriften gesetzt: {headers}")

            # Blockiere Signale während des Füllens der Tabelle
            self.table.blockSignals(True)
            
            # Fill table with data
            logger.info("Fülle Tabelle mit Daten")
            for row_idx, row_data in enumerate(results):
                col_idx = 0
                for key in visible_columns:
                    if key == 'HandlerName':
                        # Kombiniere Name und Initials für LastHandler
                        handler_name = row_data.get('HandlerName', '')
                        initials = row_data.get('LastHandler', '')
                        display_value = f"{handler_name} ({initials})" if handler_name else initials
                        item = QTableWidgetItem(display_value)
                    elif key == 'Type':
                        # Type-Mapping: Englische Werte -> Deutsche Anzeige
                        type_mapping = {
                            'repair': 'Reparatur',
                            'return': 'Widerruf',
                            'replace': 'Ersatz',
                            'refund': 'Rückerstattung',
                            'other': 'Sonstiges'
                        }
                        value = row_data.get(key)
                        display_value = type_mapping.get(value, value) if value else ''
                        item = QTableWidgetItem(display_value)
                    else:
                        value = row_data.get(key)
                        item = QTableWidgetItem(str(value) if value is not None else '')
                    
                    # Setze die Sortierreihenfolge für verschiedene Datentypen
                    if key in ['EntryDate', 'ExitDate']:
                        try:
                            date = datetime.strptime(str(value), '%Y-%m-%d').date()
                            item.setData(Qt.ItemDataRole.DisplayRole, str(value))
                            item.setData(Qt.ItemDataRole.UserRole, date)
                        except (ValueError, TypeError):
                            item.setData(Qt.ItemDataRole.DisplayRole, '')
                    elif key == 'TicketNumber':
                        try:
                            num = int(''.join(filter(str.isdigit, str(value))))
                            item.setData(Qt.ItemDataRole.DisplayRole, str(value))
                            item.setData(Qt.ItemDataRole.UserRole, num)
                        except ValueError:
                            item.setData(Qt.ItemDataRole.DisplayRole, str(value))
                    
                    # Erlaube Bearbeitung für bestimmte Spalten
                    if key in ['Status', 'Type', 'StorageLocation', 'LastHandler']:
                        # Dropdown-Spalten: Nur Auswahl erlauben
                        item.setFlags(
                            Qt.ItemFlag.ItemIsSelectable | 
                            Qt.ItemFlag.ItemIsEnabled
                        )
                    else:
                        # Normale Spalten: Vollständige Bearbeitung erlauben
                        item.setFlags(
                            Qt.ItemFlag.ItemIsSelectable | 
                            Qt.ItemFlag.ItemIsEnabled |
                            Qt.ItemFlag.ItemIsEditable
                        )
                    
                    # Visuelle Indikatoren für gelöschte Einträge
                    if self.show_deleted_entries:
                        # Graue Farbe für gelöschte Einträge
                        item.setBackground(Qt.GlobalColor.lightGray)
                        # Durchgestrichener Text
                        font = item.font()
                        font.setStrikeOut(True)
                        item.setFont(font)
                    
                    self.table.setItem(row_idx, col_idx, item)
                    col_idx += 1

            logger.info("Tabelle mit Daten gefüllt")
            
            # Aktiviere Sortierung wieder und stelle vorherige Sortierreihenfolge wieder her
            # self.table.setSortingEnabled(True)  # Entfernt - wir verwenden nur unsere benutzerdefinierte Sortierung
            if current_sort_column >= 0:
                logger.info(f"Stelle vorherige Sortierung wieder her - Spalte: {current_sort_column}, Richtung: {current_sort_order}")
                self.table.sortItems(current_sort_column, current_sort_order)
                header.setSortIndicator(current_sort_column, current_sort_order)
            
            # Signale wieder aktivieren
            self.table.blockSignals(False)
            
            # Adjust column widths
            self.table.resizeColumnsToContents()
            logger.info("Spaltenbreiten angepasst")
            
            # Status-Meldung basierend auf Ansicht
            if self.show_deleted_entries:
                self.status_bar.showMessage(f"Papierkorb: {len(results)} gelöschte Einträge geladen", 5000)
            else:
                self.status_bar.showMessage(f"Aktive Einträge: {len(results)} RMA-Einträge geladen", 5000)
            
            logger.info(f"load_rma_data erfolgreich abgeschlossen - {len(results)} Einträge geladen")

        except DatabaseConnectionError as e:
            logger.error(f"Datenbankfehler in load_rma_data: {e}")
            self._show_error("Database Error", str(e))
        except Exception as e:
            logger.exception("Unerwarteter Fehler in load_rma_data")
            self._show_error("Error", f"An unexpected error occurred: {e}")

    def _add_test_entry(self):
        """Fügt einen Dummy-RMA-Eintrag mit Produkt und RepairDetails hinzu."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                import random
                ticket_number = f"TEST-{random.randint(10000,99999)}"
                order_number = "SY12345"
                # RMA_Cases
                cursor.execute(
                    "INSERT INTO RMA_Cases (TicketNumber, OrderNumber, EntryDate, Status) VALUES (%s, %s, CURDATE(), 'Open')",
                    (ticket_number, order_number)
                )
                # RMA_Products
                cursor.execute(
                    "INSERT INTO RMA_Products (TicketNumber, OrderNumber, ProductName, SerialNumber, Quantity) VALUES (%s, %s, %s, %s, %s)",
                    (ticket_number, order_number, "TestProduct", "SN-TEST", 1)
                )
                # RMA_RepairDetails
                cursor.execute(
                    "INSERT INTO RMA_RepairDetails (TicketNumber, OrderNumber, CustomerDescription) VALUES (%s, %s, %s)",
                    (ticket_number, order_number, "Test repair entry")
                )
                conn.commit()
            self._show_success("Erfolg", f"Testeintrag {ticket_number} wurde angelegt.")
            self.load_rma_data()
        except Exception as e:
            self._show_error("Fehler", f"Testeintrag konnte nicht angelegt werden: {e}")

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Behandelt Änderungen in der Tabelle."""
        if not self.db_connection or self.show_deleted_entries:
            return
            
        row = item.row()
        column = item.column()
        new_value = item.text()
        
        # Hole Ticket-Nummer der Zeile
        ticket_item = self.table.item(row, 0)  # TicketNumber ist die erste Spalte
        if not ticket_item:
            return
            
        ticket_number = ticket_item.text()
        
        # Bestimme welche Spalte geändert wurde
        header = self.table.horizontalHeader()
        column_name = header.model().headerData(column, Qt.Orientation.Horizontal)
        
        logger.info(f"Tabellen-Änderung: {ticket_number}, Spalte: {column_name}, Wert: {new_value}")
        
        try:
            self._save_table_change(ticket_number, column_name, new_value)
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Tabellen-Änderung: {e}")
            self._show_error("Fehler", f"Änderung konnte nicht gespeichert werden: {e}")
            # Lade Daten neu um Änderung rückgängig zu machen
            self.load_rma_data()

    def _save_table_change(self, ticket_number: str, column_name: str, new_value: str) -> None:
        """Speichert eine Änderung aus der Tabelle in die Datenbank."""
        with self.db_connection.get_connection() as conn:
            cursor = conn.cursor()
            
            # Beginne Transaktion
            cursor.execute("START TRANSACTION")
            
            try:
                # Mapping von Spaltennamen zu Datenbankfeldern
                column_mapping = {
                    'OrderNumber': ('RMA_Cases', 'OrderNumber'),
                    'Type': ('RMA_Cases', 'Type'),
                    'EntryDate': ('RMA_Cases', 'EntryDate'),
                    'Status': ('RMA_Cases', 'Status'),
                    'ExitDate': ('RMA_Cases', 'ExitDate'),
                    'TrackingNumber': ('RMA_Cases', 'TrackingNumber'),
                    'IsAmazon': ('RMA_Cases', 'IsAmazon'),
                    'StorageLocation': ('RMA_Cases', 'StorageLocationID'),
                    'LastHandler': ('RMA_RepairDetails', 'LastHandler')
                }
                
                if column_name not in column_mapping:
                    logger.warning(f"Unbekannte Spalte: {column_name}")
                    return
                
                table_name, field_name = column_mapping[column_name]
                
                # Spezielle Behandlung für verschiedene Datentypen
                if column_name == 'IsAmazon':
                    # Boolean-Wert
                    bool_value = new_value.lower() in ['true', '1', 'yes', 'ja']
                    cursor.execute(
                        f"UPDATE {table_name} SET {field_name} = %s WHERE TicketNumber = %s",
                        (bool_value, ticket_number)
                    )
                elif column_name in ['EntryDate', 'ExitDate']:
                    # Datum-Wert
                    if new_value and new_value.strip():
                        try:
                            from datetime import datetime
                            date_value = datetime.strptime(new_value, '%Y-%m-%d').date()
                            cursor.execute(
                                f"UPDATE {table_name} SET {field_name} = %s WHERE TicketNumber = %s",
                                (date_value, ticket_number)
                            )
                        except ValueError:
                            logger.error(f"Ungültiges Datum: {new_value}")
                            raise Exception(f"Ungültiges Datum: {new_value}")
                    else:
                        # Leeres Datum auf NULL setzen
                        cursor.execute(
                            f"UPDATE {table_name} SET {field_name} = NULL WHERE TicketNumber = %s",
                            (ticket_number,)
                        )
                elif column_name == 'StorageLocation':
                    # StorageLocation ID aus Namen finden
                    if new_value:
                        location_query = "SELECT ID FROM StorageLocations WHERE LocationName = %s"
                        location_result = self.db_connection.execute_query(location_query, (new_value,))
                        if location_result:
                            location_id = location_result[0]['ID']
                            cursor.execute(
                                f"UPDATE {table_name} SET {field_name} = %s WHERE TicketNumber = %s",
                                (location_id, ticket_number)
                            )
                        else:
                            logger.warning(f"Lagerort nicht gefunden: {new_value}")
                    else:
                        cursor.execute(
                            f"UPDATE {table_name} SET {field_name} = NULL WHERE TicketNumber = %s",
                            (ticket_number,)
                        )
                elif column_name == 'LastHandler':
                    # Handler Initials aus Namen extrahieren
                    if new_value:
                        # Extrahiere Initials aus "Name (Initials)" Format
                        if '(' in new_value and ')' in new_value:
                            initials = new_value.split('(')[1].split(')')[0]
                        else:
                            initials = new_value
                        
                        cursor.execute(
                            f"UPDATE {table_name} SET {field_name} = %s WHERE TicketNumber = %s",
                            (initials, ticket_number)
                        )
                    else:
                        cursor.execute(
                            f"UPDATE {table_name} SET {field_name} = NULL WHERE TicketNumber = %s",
                            (ticket_number,)
                        )
                elif column_name == 'Type':
                    # Type-Mapping: Deutsche Anzeige -> Englische Werte
                    type_mapping = {
                        'Reparatur': 'repair',
                        'Widerruf': 'return',
                        'Ersatz': 'replace',
                        'Rückerstattung': 'refund',
                        'Sonstiges': 'other'
                    }
                    
                    # Konvertiere deutschen Namen zu englischem Wert
                    db_value = type_mapping.get(new_value, new_value)
                    cursor.execute(
                        f"UPDATE {table_name} SET {field_name} = %s WHERE TicketNumber = %s",
                        (db_value, ticket_number)
                    )
                else:
                    # Standard-String-Wert
                    cursor.execute(
                        f"UPDATE {table_name} SET {field_name} = %s WHERE TicketNumber = %s",
                        (new_value, ticket_number)
                    )
                
                # Commit Transaktion
                cursor.execute("COMMIT")
                logger.info(f"Änderung gespeichert: {ticket_number}, {column_name} = {new_value}")
                
            except Exception as e:
                # Bei Fehler Rollback
                cursor.execute("ROLLBACK")
                logger.error(f"Fehler beim Speichern - Rollback durchgeführt: {e}")
                raise e

    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        """Behandelt Doppelklick auf Tabellenzellen für Dropdowns."""
        if self.show_deleted_entries:
            return
            
        header = self.table.horizontalHeader()
        column_name = header.model().headerData(column, Qt.Orientation.Horizontal)
        
        # Nur für Dropdown-Spalten
        if column_name not in ['Status', 'Type', 'StorageLocation', 'LastHandler']:
            return
            
        # Erstelle Dropdown-Dialog
        self._show_dropdown_dialog(row, column, column_name)

    def _show_dropdown_dialog(self, row: int, column: int, column_name: str) -> None:
        """Zeigt einen Dropdown-Dialog für die ausgewählte Zelle."""
        from PySide6.QtWidgets import QComboBox, QDialog, QVBoxLayout, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{column_name} auswählen")
        dialog.setModal(True)
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # Erstelle ComboBox
        combo = QComboBox()
        
        # Fülle ComboBox basierend auf Spalte
        if column_name == 'Status':
            combo.addItems(['Open', 'In Progress', 'Completed', 'Closed'])
        elif column_name == 'Type':
            # Deutsche Anzeige für Type-Werte
            type_mapping = {
                'Reparatur': 'repair',
                'Widerruf': 'return',
                'Ersatz': 'replace',
                'Rückerstattung': 'refund',
                'Sonstiges': 'other'
            }
            
            # Zeige deutsche Namen an, speichere englische Werte
            combo.addItems(list(type_mapping.keys()))
            
            # Speichere Mapping für späteren Zugriff
            combo.setProperty('type_mapping', type_mapping)
        elif column_name == 'StorageLocation':
            # Lade Lagerorte aus Datenbank
            try:
                locations_query = "SELECT LocationName FROM StorageLocations ORDER BY LocationName"
                locations_result = self.db_connection.execute_query(locations_query)
                if locations_result:
                    location_names = [row['LocationName'] for row in locations_result]
                    combo.addItems([''] + location_names)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Lagerorte: {e}")
        elif column_name == 'LastHandler':
            # Lade Handler aus Datenbank
            try:
                handlers_query = "SELECT Name, Initials FROM Handlers ORDER BY Name"
                handlers_result = self.db_connection.execute_query(handlers_query)
                if handlers_result:
                    handler_names = [f"{row['Name']} ({row['Initials']})" for row in handlers_result]
                    combo.addItems([''] + handler_names)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Handler: {e}")
        
        # Setze aktuellen Wert
        current_item = self.table.item(row, column)
        if current_item:
            current_text = current_item.text()
            index = combo.findText(current_text)
            if index >= 0:
                combo.setCurrentIndex(index)
        
        layout.addWidget(combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Abbrechen")
        
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Zeige Dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_value = combo.currentText()
            if new_value != current_item.text() if current_item else True:
                # Aktualisiere Tabellenzelle
                if not current_item:
                    current_item = QTableWidgetItem()
                    self.table.setItem(row, column, current_item)
                current_item.setText(new_value)
                
                # Speichere in Datenbank
                ticket_item = self.table.item(row, 0)
                if ticket_item:
                    ticket_number = ticket_item.text()
                    try:
                        self._save_table_change(ticket_number, column_name, new_value)
                    except Exception as e:
                        logger.error(f"Fehler beim Speichern der Dropdown-Änderung: {e}")
                        self._show_error("Fehler", f"Änderung konnte nicht gespeichert werden: {e}")

    def _create_new_entry(self) -> None:
        """Öffnet den Dialog zum Erstellen eines neuen RMA-Eintrags."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return
            
        if self.show_deleted_entries:
            self._show_error("Fehler", "Neue Einträge können nur in der aktiven Ansicht erstellt werden")
            return
            
        dialog = EntryDialog(
            parent=self,
            db_connection=self.db_connection,
            is_edit_mode=False
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_rma_data()
            self._show_success("Erfolg", "Neuer RMA-Eintrag wurde erstellt")

    def _edit_selected_entry(self) -> None:
        """Öffnet den Dialog zum Bearbeiten des ausgewählten RMA-Eintrags."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return
            
        if self.show_deleted_entries:
            self._show_error("Fehler", "Gelöschte Einträge können nicht bearbeitet werden")
            return
            
        rma_numbers = self._get_selected_rma_numbers()
        
        if not rma_numbers:
            self._show_error("Fehler", "Bitte wählen Sie einen Eintrag zum Bearbeiten aus")
            return
            
        if len(rma_numbers) > 1:
            self._show_error("Fehler", "Bitte wählen Sie nur einen Eintrag zum Bearbeiten aus")
            return
            
        ticket_number = rma_numbers[0]
        
        dialog = EntryDialog(
            parent=self,
            db_connection=self.db_connection,
            ticket_number=ticket_number,
            is_edit_mode=True
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_rma_data()
            self._show_success("Erfolg", f"RMA-Eintrag {ticket_number} wurde aktualisiert")

    def _toggle_trash_view(self) -> None:
        """Wechselt zwischen aktiven Einträgen und Papierkorb-Ansicht."""
        self.show_deleted_entries = not self.show_deleted_entries
        
        # Aktualisiere Toolbar-Aktionen
        if self.show_deleted_entries:
            self.trash_toggle_action.setText("Aktive Einträge anzeigen")
            self.trash_toggle_action.setStatusTip("Wechselt zurück zu aktiven Einträgen")
            self.restore_action.setVisible(True)
            self.delete_action.setVisible(False)  # Verstecke Löschen-Button im Papierkorb
        else:
            self.trash_toggle_action.setText("Papierkorb anzeigen")
            self.trash_toggle_action.setStatusTip("Wechselt zur Papierkorb-Ansicht")
            self.restore_action.setVisible(False)
            self.delete_action.setVisible(True)  # Zeige Löschen-Button bei aktiven Einträgen
        
        # Lade Daten neu
        self.load_rma_data()
        
        # Aktualisiere Status
        status_text = "Papierkorb-Ansicht" if self.show_deleted_entries else "Aktive Einträge"
        self.status_bar.showMessage(f"Ansicht gewechselt: {status_text}", 3000)

    def _restore_selected_entries(self) -> None:
        """Stellt die ausgewählten Einträge aus dem Papierkorb wieder her."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return

        rma_numbers = self._get_selected_rma_numbers()
        logger.info(f"Wiederherstellung angefordert für {len(rma_numbers)} Einträge: {rma_numbers}")
        
        if not rma_numbers:
            self._show_error("Fehler", "Bitte wählen Sie mindestens einen Eintrag aus")
            return

        # Bestätigungsdialog anzeigen
        reply = QMessageBox.question(
            self, 
            "Wiederherstellung bestätigen",
            f"Möchten Sie {len(rma_numbers)} Einträge aus dem Papierkorb wiederherstellen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            logger.info("Wiederherstellung vom Benutzer abgebrochen")
            return

        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Beginne Transaktion
                cursor.execute("START TRANSACTION")
                logger.info("Datenbank-Transaktion für Wiederherstellung gestartet")
                
                try:
                    # Wiederherstellung für RMA_Cases
                    logger.info(f"Stelle RMA_Cases wieder her - {len(rma_numbers)} Einträge")
                    cursor.execute(
                        """
                        UPDATE RMA_Cases 
                        SET IsDeleted = FALSE, 
                            DeletedAt = NULL,
                            DeletedBy = NULL
                        WHERE TicketNumber IN %s
                        """,
                        (rma_numbers,)
                    )
                    cases_updated = cursor.rowcount
                    logger.info(f"RMA_Cases wiederhergestellt: {cases_updated} Zeilen betroffen")
                    
                    # Wiederherstellung für zugehörige Daten
                    logger.info("Stelle RMA_RepairDetails wieder her")
                    cursor.execute(
                        """
                        UPDATE RMA_RepairDetails 
                        SET IsDeleted = FALSE,
                            DeletedAt = NULL,
                            DeletedBy = NULL
                        WHERE TicketNumber IN %s
                        """,
                        (rma_numbers,)
                    )
                    repair_details_updated = cursor.rowcount
                    logger.info(f"RMA_RepairDetails wiederhergestellt: {repair_details_updated} Zeilen betroffen")
                    
                    logger.info("Stelle RMA_Products wieder her")
                    cursor.execute(
                        """
                        UPDATE RMA_Products 
                        SET IsDeleted = FALSE,
                            DeletedAt = NULL,
                            DeletedBy = NULL
                        WHERE TicketNumber IN %s
                        """,
                        (rma_numbers,)
                    )
                    products_updated = cursor.rowcount
                    logger.info(f"RMA_Products wiederhergestellt: {products_updated} Zeilen betroffen")
                    
                    # Commit Transaktion
                    cursor.execute("COMMIT")
                    logger.info("Datenbank-Transaktion für Wiederherstellung erfolgreich committed")
                    
                    self._show_success(
                        "Erfolg",
                        f"{len(rma_numbers)} RMA-Einträge wurden wiederhergestellt"
                    )
                    
                    # Tabelle aktualisieren
                    logger.info("Lade RMA-Daten neu nach Wiederherstellung")
                    self.load_rma_data()
                    
                except Exception as e:
                    # Bei Fehler Rollback
                    cursor.execute("ROLLBACK")
                    logger.error(f"Fehler während Wiederherstellung - Rollback durchgeführt: {e}")
                    raise e
                    
        except DatabaseConnectionError as e:
            logger.error(f"Datenbankverbindungsfehler bei Wiederherstellung: {e}")
            self._show_error("Datenbankfehler", str(e))
        except Exception as e:
            logger.exception("Fehler bei der Wiederherstellung der Einträge")
            self._show_error("Fehler", f"Unerwarteter Fehler: {e}")

    def _permanent_delete_selected_entries(self) -> None:
        """Löscht die ausgewählten Einträge endgültig aus der Datenbank."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return

        rma_numbers = self._get_selected_rma_numbers()
        logger.info(f"Endgültiges Löschen angefordert für {len(rma_numbers)} Einträge: {rma_numbers}")
        
        if not rma_numbers:
            self._show_error("Fehler", "Bitte wählen Sie mindestens einen Eintrag aus")
            return

        # Warnung anzeigen
        reply = QMessageBox.warning(
            self, 
            "Endgültiges Löschen",
            f"ACHTUNG: Diese Aktion kann nicht rückgängig gemacht werden!\n\n"
            f"Möchten Sie {len(rma_numbers)} Einträge endgültig löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            logger.info("Endgültiges Löschen vom Benutzer abgebrochen")
            return

        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Beginne Transaktion
                cursor.execute("START TRANSACTION")
                logger.info("Datenbank-Transaktion für endgültiges Löschen gestartet")
                
                try:
                    # Endgültiges Löschen für alle zugehörigen Daten
                    logger.info("Lösche RMA_RepairDetails endgültig")
                    cursor.execute(
                        "DELETE FROM RMA_RepairDetails WHERE TicketNumber IN %s",
                        (rma_numbers,)
                    )
                    repair_details_deleted = cursor.rowcount
                    
                    logger.info("Lösche RMA_Products endgültig")
                    cursor.execute(
                        "DELETE FROM RMA_Products WHERE TicketNumber IN %s",
                        (rma_numbers,)
                    )
                    products_deleted = cursor.rowcount
                    
                    logger.info("Lösche RMA_Cases endgültig")
                    cursor.execute(
                        "DELETE FROM RMA_Cases WHERE TicketNumber IN %s",
                        (rma_numbers,)
                    )
                    cases_deleted = cursor.rowcount
                    
                    # Commit Transaktion
                    cursor.execute("COMMIT")
                    logger.info("Datenbank-Transaktion für endgültiges Löschen erfolgreich committed")
                    
                    self._show_success(
                        "Erfolg",
                        f"{len(rma_numbers)} RMA-Einträge wurden endgültig gelöscht"
                    )
                    
                    # Tabelle aktualisieren
                    logger.info("Lade RMA-Daten neu nach endgültigem Löschen")
                    self.load_rma_data()
                    
                except Exception as e:
                    # Bei Fehler Rollback
                    cursor.execute("ROLLBACK")
                    logger.error(f"Fehler während endgültigem Löschen - Rollback durchgeführt: {e}")
                    raise e
                    
        except DatabaseConnectionError as e:
            logger.error(f"Datenbankverbindungsfehler beim endgültigen Löschen: {e}")
            self._show_error("Datenbankfehler", str(e))
        except Exception as e:
            logger.exception("Fehler beim endgültigen Löschen der Einträge")
            self._show_error("Fehler", f"Unerwarteter Fehler: {e}")

    def _handle_sort(self, logical_index: int) -> None:
        """Behandelt das Sortieren der Tabelle.
        
        Args:
            logical_index: Index der geklickten Spalte
        """
        header = self.table.horizontalHeader()
        current_section = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()
        
        logger.info(f"Sortierung angefordert - Spalte: {logical_index}, Aktuelle Spalte: {current_section}, Aktuelle Richtung: {current_order}")
        
        # Wenn die gleiche Spalte nochmal geklickt wird, wechsle die Sortierrichtung
        if current_section == logical_index:
            # Wechsle die Sortierrichtung
            new_order = (Qt.SortOrder.AscendingOrder 
                        if current_order == Qt.SortOrder.DescendingOrder 
                        else Qt.SortOrder.DescendingOrder)
            logger.info(f"Gleiche Spalte geklickt - Wechsle Richtung von {current_order} zu {new_order}")
        else:
            # Neue Spalte: Standardmäßig aufsteigend sortieren
            new_order = Qt.SortOrder.AscendingOrder
            logger.info(f"Neue Spalte geklickt - Setze Richtung auf {new_order}")
        
        # Aktualisiere den Sortierindikator zuerst
        header.setSortIndicator(logical_index, new_order)
        logger.info(f"Sortierindikator gesetzt - Spalte: {logical_index}, Richtung: {new_order}")
        
        # Sortiere die Tabelle
        self.table.sortItems(logical_index, new_order)
        logger.info(f"Tabelle sortiert - Spalte: {logical_index}, Richtung: {new_order}")
        
        # Stelle sicher, dass die Sortierung aktiviert ist
        if not self.table.isSortingEnabled():
            self.table.setSortingEnabled(True)
            logger.info("Sortierung wurde aktiviert")

class DeleteConfirmationDialog(QDialog):
    """Dialog zur Bestätigung des Archivierens von RMA-Einträgen."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        rma_numbers: Optional[List[str]] = None
    ) -> None:
        """Initialisiert den Archivierungs-Bestätigungsdialog.
        
        Args:
            parent: Parent-Widget
            rma_numbers: Liste der zu archivierenden RMA-Nummern
        """
        super().__init__(parent)
        self.rma_numbers = rma_numbers or []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Richtet die Benutzeroberfläche ein."""
        self.setWindowTitle("RMA-Einträge archivieren")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Warnung
        warning_label = QLabel(
            "Warnung: Diese Aktion verschiebt die Einträge in das Archiv!"
        )
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(warning_label)
        
        # Liste der zu archivierenden Einträge
        if self.rma_numbers:
            entries_label = QLabel(
                f"Folgende RMA-Einträge werden archiviert:\n" +
                "\n".join(f"- {rma}" for rma in self.rma_numbers)
            )
            layout.addWidget(entries_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        archive_button = QPushButton("Archivieren")
        archive_button.setStyleSheet("background-color: #ffc107; color: black;")
        archive_button.clicked.connect(self._confirm_delete)
        button_layout.addWidget(archive_button)
        
        layout.addLayout(button_layout)

    def _confirm_delete(self) -> None:
        """Zeigt eine letzte Bestätigung an und akzeptiert den Dialog."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Letzte Bestätigung")
        msg.setText("Sind Sie sicher, dass Sie diese Einträge archivieren möchten?")
        msg.setInformativeText("Die Einträge können später wiederhergestellt werden.")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.accept()

def main() -> None:
    """Start the RMA Database GUI application."""
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")  # Use Fusion style for consistent look across platforms
        
        # Set application-wide font
        font = QFont("Segoe UI", 10)
        app.setFont(font)
        
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.exception("Application failed to start")
        LoggingMessageBox.critical(None, "Fatal Error", f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 