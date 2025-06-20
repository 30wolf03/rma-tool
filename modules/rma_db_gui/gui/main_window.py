"""Main window for the RMA Database GUI.

This module provides the main application window with a modern, user-friendly
interface for managing RMA database entries.
"""

from __future__ import annotations

import sys
from typing import Optional, List
from datetime import datetime

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QAction
from PyQt6.QtWidgets import (
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

# Import the credential cache
from shared.credentials.credential_cache import get_credential_cache
from shared.credentials.keepass_handler import CentralKeePassHandler

# Configure logging
logger.remove()  # Remove default handler

# Log in die Konsole
logger.add(sys.stderr, level=LOG_LEVEL, format=LOG_FORMAT)

# Log in die Datei
logger.add(str(get_log_file()), level=LOG_LEVEL, format=LOG_FORMAT, encoding="utf-8")

class TicketDetailsDialog(QDialog):
    """Dialog zur Anzeige der Ticket-Details."""
    
    def __init__(self, parent: QMainWindow, ticket_number: str, db_connection: DatabaseConnection) -> None:
        """Initialisiert den Detail-Dialog.
        
        Args:
            parent: Parent-Window
            ticket_number: Die Ticket-Nummer
            db_connection: Die Datenbankverbindung
        """
        super().__init__(parent)
        self.ticket_number = ticket_number
        self.db_connection = db_connection
        self.setWindowTitle(f"Ticket Details - {ticket_number}")
        self.setMinimumWidth(600)
        self._setup_ui()
        self._load_details()
        
    def _setup_ui(self) -> None:
        """Richtet die Benutzeroberfläche ein."""
        layout = QVBoxLayout(self)
        
        # Formular für die Details
        form_layout = QFormLayout()
        
        # Allgemeine Informationen
        self.customer_desc = QTextEdit()
        self.customer_desc.setReadOnly(True)
        form_layout.addRow("Kundenbeschreibung:", self.customer_desc)
        
        self.problem_cause = QTextEdit()
        self.problem_cause.setReadOnly(True)
        form_layout.addRow("Problemursache:", self.problem_cause)
        
        self.last_action = QLabel()
        form_layout.addRow("Letzte Aktion:", self.last_action)
        
        self.last_handler = QLabel()
        form_layout.addRow("Letzter Bearbeiter:", self.last_handler)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def _load_details(self) -> None:
        """Lädt die Ticket-Details aus der Datenbank."""
        try:
            # Lade RepairDetails
            results = self.db_connection.execute_query("""
                SELECT 
                    rd.CustomerDescription,
                    rd.ProblemCause,
                    rd.LastAction,
                    rd.LastHandler,
                    h.Name as HandlerName
                FROM RMA_RepairDetails rd
                LEFT JOIN Handlers h ON rd.LastHandler = h.Initials
                WHERE rd.TicketNumber = %s
            """, (self.ticket_number,))
            
            if results:
                row = results[0]
                self.customer_desc.setText(row['CustomerDescription'] or '')
                self.problem_cause.setText(row['ProblemCause'] or '')
                self.last_action.setText(row['LastAction'] or '')
                self.last_handler.setText(f"{row['HandlerName']} ({row['LastHandler']})" if row['HandlerName'] else row['LastHandler'] or '')
                
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der Details: {e}")

class MainWindow(QMainWindow):
    """Main window for the RMA Database GUI.

    This class provides a modern, user-friendly interface for managing
    RMA database entries with proper error handling and status feedback.
    """

    def __init__(self) -> None:
        """Initialize the main window.
        
        Args:
            central_kp_handler: Der zentrale KeePass-Handler mit den gespeicherten Credentials
        """
        super().__init__()
        self.credential_cache = get_credential_cache()
        # Hole zentralen Handler aus Cache
        self.central_kp_handler = self.credential_cache.get_keepass_handler()
        if not self.central_kp_handler or not self.central_kp_handler.is_database_open():
            QMessageBox.critical(self, "Fehler", "Keine zentrale Authentifizierung gefunden. Bitte Anwendung neu starten.")
            sys.exit(1)
        self._setup_ui()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_connections()
        try:
            self.db_connection = DatabaseConnection(self.central_kp_handler)
            self._show_success("Erfolg", "Erfolgreich mit der Datenbank verbunden!")
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
        delete_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            "Löschen",
            self
        )
        delete_action.setStatusTip("Ausgewählte RMA-Einträge löschen")
        delete_action.triggered.connect(self._delete_selected_entries)
        toolbar.addAction(delete_action)

        # Refresh action
        refresh_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            "Aktualisieren",
            self
        )
        refresh_action.setStatusTip("RMA-Daten aktualisieren")
        refresh_action.triggered.connect(self.load_rma_data)
        toolbar.addAction(refresh_action)

        # Testeintrag anlegen
        add_test_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Testeintrag anlegen",
            self
        )
        add_test_action.setStatusTip("Fügt einen Dummy-RMA-Eintrag zum Testen hinzu")
        add_test_action.triggered.connect(self._add_test_entry)
        toolbar.addAction(add_test_action)

        # Context menu for table
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position) -> None:
        """Zeigt das Kontextmenü für die Tabelle an."""
        menu = QMenu()
        
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
        QMessageBox.critical(self, title, message)
        self.status_bar.showMessage(f"Error: {message}", 5000)

    def _show_success(self, title: str, message: str) -> None:
        """Show a success message dialog.

        Args:
            title: The dialog title.
            message: The success message to display.
        """
        QMessageBox.information(self, title, message)
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

    def _show_ticket_details(self, row: int, column: int) -> None:
        """Zeigt den Detail-Dialog für das ausgewählte Ticket an."""
        if not self.db_connection:
            return
            
        ticket_item = self.table.item(row, 0)  # TicketNumber ist die erste Spalte
        if ticket_item:
            ticket_number = ticket_item.text()
            dialog = TicketDetailsDialog(self, ticket_number, self.db_connection)
            dialog.exec()

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
            # Zeige nur die relevanten Spalten an
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
                else:
                    headers.append(col)
            self.table.setHorizontalHeaderLabels(headers)
            logger.info(f"Spaltenüberschriften gesetzt: {headers}")

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
                    
                    # Erlaube Textauswahl, aber keine Bearbeitung
                    item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable | 
                        Qt.ItemFlag.ItemIsEnabled |
                        Qt.ItemFlag.ItemIsEditable  # Erlaubt Textauswahl
                    )
                    self.table.setItem(row_idx, col_idx, item)
                    col_idx += 1

            logger.info("Tabelle mit Daten gefüllt")
            
            # Aktiviere Sortierung wieder und stelle vorherige Sortierreihenfolge wieder her
            # self.table.setSortingEnabled(True)  # Entfernt - wir verwenden nur unsere benutzerdefinierte Sortierung
            if current_sort_column >= 0:
                logger.info(f"Stelle vorherige Sortierung wieder her - Spalte: {current_sort_column}, Richtung: {current_sort_order}")
                self.table.sortItems(current_sort_column, current_sort_order)
                header.setSortIndicator(current_sort_column, current_sort_order)
            
            # Adjust column widths
            self.table.resizeColumnsToContents()
            logger.info("Spaltenbreiten angepasst")
            self.status_bar.showMessage(f"Loaded {len(results)} RMA entries", 5000)
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
        QMessageBox.critical(None, "Fatal Error", f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 