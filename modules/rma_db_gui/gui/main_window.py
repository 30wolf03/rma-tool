"""Main window for the RMA Database GUI.

This module provides the main application window with a modern, user-friendly
interface for managing RMA database entries.
"""

from __future__ import annotations

import sys
import threading
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QFont, QAction, QKeyEvent, QColor
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
from shared.utils.unified_logger import get_logger

from ..database.connection import DatabaseConnection, DatabaseConnectionError
from ..utils.keepass_handler import KeepassHandler, KeepassError
from .dialogs import DeleteConfirmationDialog
from .login_window import LoginDialog
from .entry_dialog import EntryDialog

# Import the credential cache
from shared.credentials.credential_cache import get_credential_cache
from shared.credentials.keepass_handler import CentralKeePassHandler

# Einheitliches Logging-System verwenden
logger = get_logger("RMA-Database-GUI")

# Lokale Konstanten
WINDOW_TITLE = "RMA Database GUI"
WINDOW_SIZE = (800, 600)


class MainWindow(QMainWindow):
    """Main window for the RMA Database GUI.

    This class provides a modern, user-friendly interface for managing
    RMA database entries with proper error handling and status feedback.
    """

    def __init__(self, current_user: str = "MWO") -> None:
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
        self.current_user = current_user  # Jetzt dynamisch gesetzt

        # Dark Mode Status
        self.dark_mode_enabled = False
        
        # --- Automatisches Polling ---
        from shared.config.settings import Settings
        self.settings = Settings()
        module_settings = self.settings.get_module_settings("rma_db_gui")
        self.auto_refresh_interval = module_settings.get("auto_refresh_interval", 30)
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self.load_rma_data)
        self._auto_refresh_timer.start(self.auto_refresh_interval * 1000)
        # ---
        
        # Optimistic-Update Zustände
        # key: (ticket_number, column_name) -> { 'old_value': str, 'new_value': str }
        self._pending_updates: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._suppress_table_change: bool = False
        self._row_by_ticket: Dict[str, int] = {}

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

        # Password input section removed - using central authentication

        # Search section
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)

        # Search label
        search_label = QLabel("Suche:")
        search_label.setFont(QFont("Segoe UI", 10))
        search_layout.addWidget(search_label)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setFont(QFont("Segoe UI", 10))
        self.search_input.setPlaceholderText("Ticket-Nummer, Auftragsnummer oder Produktname...")
        self.search_input.textChanged.connect(self._filter_table)
        search_layout.addWidget(self.search_input)

        # Clear search button
        clear_search_button = QPushButton("X")
        clear_search_button.setMaximumWidth(30)
        clear_search_button.clicked.connect(self._clear_search)
        search_layout.addWidget(clear_search_button)

        main_layout.addWidget(search_widget)

        # Create table
        self.table = QTableWidget()
        self.table.setFont(QFont("Segoe UI", 9))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Sortierung aktivieren
        self.table.setSortingEnabled(True)
        
        # Setze Header-Eigenschaften für bessere Sortierung
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setStretchLastSection(True)
        
        # Keyboard-Events für Delete-Funktionalität
        self.table.keyPressEvent = self._table_key_press_event
        
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
        refresh_action.setStatusTip("Tabelle neu laden")
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

        # Eintrag bearbeiten
        edit_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Eintrag bearbeiten",
            self
        )
        edit_action.setStatusTip("Bearbeitet den ausgewählten RMA-Eintrag")
        edit_action.triggered.connect(self._edit_selected_entry)
        toolbar.addAction(edit_action)

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

        # Dark Mode Toggle
        self.dark_mode_action = QAction(
            "🌙 Dark Mode",
            self
        )
        self.dark_mode_action.setStatusTip("Dark Mode ein-/ausschalten")
        self.dark_mode_action.triggered.connect(self._toggle_dark_mode)
        self.dark_mode_action.setCheckable(True)
        toolbar.addAction(self.dark_mode_action)

        # Context menu for table
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Verbinde Tabellen-Änderungen
        self.table.itemChanged.connect(self._on_table_item_changed)
        
        # Verbinde Doppelklick für Dropdown-Spalten
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        # Speichere ursprüngliche Daten für Suche
        self.original_data = []

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
        # Anzeige des eingeloggten Nutzers
        self.user_label = QLabel(f"Eingeloggt als: {self.current_user}")
        self.user_label.setStyleSheet("color: #555; font-weight: bold; margin-left: 20px;")
        self.status_bar.addPermanentWidget(self.user_label)
        self.status_bar.showMessage("Ready")

    def _setup_connections(self) -> None:
        # Sortierung-Signal für Logging verbinden
        header = self.table.horizontalHeader()
        header.sortIndicatorChanged.connect(self._log_sort)
        # Tabellen-Änderungen verbinden
        self.table.itemChanged.connect(self._on_table_item_changed)

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
            
            # Qt übernimmt die Sortierung automatisch

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

            # Speichere ursprüngliche Daten für Suche
            self.original_data = results.copy() if results else []

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
                    elif key in ['EntryDate', 'ExitDate']:
                        # Datum-Spalten: Direkte Bearbeitung erlauben
                        item.setFlags(
                            Qt.ItemFlag.ItemIsSelectable | 
                            Qt.ItemFlag.ItemIsEnabled |
                            Qt.ItemFlag.ItemIsEditable
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

            # Bedingte Formatierung anwenden
            self._apply_conditional_formatting()
            
            logger.info("Tabelle mit Daten gefüllt")
            
            # Qt übernimmt die Sortierung automatisch, da setSortingEnabled(True) gesetzt ist
            # Die Sortierung wird durch das sortIndicatorChanged Signal automatisch wiederhergestellt
            
            # Signale wieder aktivieren
            self.table.blockSignals(False)
            
            # Sicherstellen, dass itemChanged Verbindung besteht
            try:
                self.table.itemChanged.disconnect(self._on_table_item_changed)
            except TypeError:
                pass  # War nicht verbunden
            self.table.itemChanged.connect(self._on_table_item_changed)
            
            # Adjust column widths
            self.table.resizeColumnsToContents()
            logger.info("Spaltenbreiten angepasst")
            
            # Baue Zeilen-Index nach TicketNumber auf (für Optimistic-Update-Reapply)
            self._rebuild_row_index_by_ticket()

            # Ausstehende (optimistische) Änderungen nach dem Reload wieder anwenden
            self._reapply_pending_overlays()

            # Status-Meldung basierend auf Ansicht
            if self.show_deleted_entries:
                self.status_bar.showMessage(f"Papierkorb: {len(results)} archivierte Einträge", 5000)
            else:
                self.status_bar.showMessage(f"Aktive Einträge: {len(results)} RMA-Fälle", 5000)
                
            # Aktualisiere Suchfeld, falls Daten gefiltert sind
            if hasattr(self, 'search_input') and self.search_input.text().strip():
                self._filter_table()
            
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

        # Unterdrücke programmatische Änderungen (z. B. beim optimistischen Setzen)
        if getattr(self, "_suppress_table_change", False):
            return
            
        row = item.row()
        column = item.column()
        new_value = item.text().strip()
        
        # Hole Ticket-Nummer der Zeile
        ticket_item = self.table.item(row, 0)  # TicketNumber ist die erste Spalte
        if not ticket_item:
            return
            
        ticket_number = ticket_item.text().strip()
        
        # Bestimme welche Spalte geändert wurde
        header = self.table.horizontalHeader()
        column_name = header.model().headerData(column, Qt.Orientation.Horizontal)
        
        # Prüfe ob es eine neue Zeile ist (leere Ticket-Nummer)
        is_new_row = not ticket_number
        
        logger.info(f"Tabellen-Änderung: {ticket_number or 'NEUE ZEILE'}, Spalte: {column_name}, Wert: {new_value}")
        
        # Für neue Zeilen: Erstelle Eintrag wenn Ticket-Nummer eingegeben wurde
        if is_new_row and column_name == 'TicketNumber' and new_value:
            try:
                self._create_new_database_entry(new_value)
                # Entferne gelbe Markierung
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 255, 255))  # Weiß
                self.status_bar.showMessage("Neuer Eintrag erstellt", 2000)
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des neuen Eintrags: {e}")
                self._show_error("Fehler", f"Eintrag konnte nicht erstellt werden: {e}")
                return
        
        # Speichere Änderung in Datenbank (nur für existierende Einträge)
        elif ticket_number:
            # Optimistisches Speichern für direkte Tabellenedits
            try:
                # Old-Value aus original_data ermitteln (falls vorhanden)
                old_value = None
                try:
                    # Mappe Column-Header auf Schlüssel in original_data
                    data_key = column_name
                    for row_data in self.original_data:
                        if row_data.get('TicketNumber') == ticket_number:
                            old_value = row_data.get(data_key)
                            break
                except Exception:
                    old_value = None

                # UI-Pending markieren (Text ist bereits gesetzt)
                self._mark_cell_pending(row, column)
                # Pending-Info registrieren
                self._pending_updates[(ticket_number, column_name)] = {
                    'old_value': '' if old_value is None else str(old_value),
                    'new_value': new_value,
                }

                # Hintergrundspeichern
                def _save_in_background():
                    try:
                        self._save_table_change(ticket_number, column_name, new_value)
                        QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, True))
                    except Exception as e:  # noqa: BLE001
                        logger.error(f"Fehler beim Speichern im Hintergrund: {e}")
                        QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, False, str(e)))

                threading.Thread(target=_save_in_background, daemon=True).start()
            except Exception as e:
                logger.error(f"Fehler beim Start des optimistischen Speicherns: {e}")
                self._show_error("Fehler", f"Änderung konnte nicht gespeichert werden: {e}")
                # Kein reload hier, UI bleibt mit neuem Wert, Nutzer kann erneut versuchen

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
                    # Akzeptiere sowohl ID als auch Namen, aber im GUI wird immer der Name angezeigt
                    location_id = None
                    if new_value is not None and str(new_value).isdigit():
                        # Wenn eine ID übergeben wird (z.B. aus dem Dropdown-Dialog)
                        location_id = int(new_value)
                    elif new_value:
                        # Wenn ein Name übergeben wird (z.B. durch direkte Eingabe)
                        location_query = "SELECT ID FROM StorageLocations WHERE LocationName = %s"
                        location_result = self.db_connection.execute_query(location_query, (new_value,))
                        if location_result:
                            location_id = location_result[0]['ID']
                        else:
                            logger.warning(f"Lagerort nicht gefunden: {new_value}")
                    if location_id is not None:
                        cursor.execute(
                            f"UPDATE {table_name} SET {field_name} = %s WHERE TicketNumber = %s",
                            (location_id, ticket_number)
                        )
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
        
        # Nur für Dropdown-Spalten und Datum-Spalten
        if column_name not in ['Status', 'Type', 'StorageLocation', 'LastHandler', 'EntryDate', 'ExitDate']:
            return
            
        # Erstelle Dropdown-Dialog
        self._show_dropdown_dialog(row, column, column_name)

    def _show_dropdown_dialog(self, row: int, column: int, column_name: str) -> None:
        """Zeigt einen Dropdown-Dialog für die ausgewählte Zelle."""
        from PySide6.QtWidgets import QComboBox, QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QDateEdit, QLabel
        from PySide6.QtCore import QDate
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{column_name} auswählen")
        dialog.setModal(True)
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # Erstelle Widget basierend auf Spalte
        if column_name in ['EntryDate', 'ExitDate']:
            # Datumsauswahl für Datum-Spalten
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("dd.MM.yyyy")
            
            # Setze aktuellen Wert
            current_item = self.table.item(row, column)
            if current_item and current_item.text().strip():
                try:
                    from datetime import datetime
                    current_date = datetime.strptime(current_item.text(), "%Y-%m-%d").date()
                    date_edit.setDate(QDate(current_date.year, current_date.month, current_date.day))
                except ValueError:
                    # Falls das Datum nicht im erwarteten Format ist, setze heutiges Datum
                    date_edit.setDate(QDate.currentDate())
            else:
                # Falls kein Datum vorhanden, setze heutiges Datum
                date_edit.setDate(QDate.currentDate())
            
            layout.addWidget(QLabel(f"{column_name} auswählen:"))
            layout.addWidget(date_edit)
            
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
                selected_date = date_edit.date()
                formatted_date = selected_date.toString("yyyy-MM-dd")
                
                # Optimistisches Update
                ticket_item = self.table.item(row, 0)
                if ticket_item:
                    ticket_number = ticket_item.text()
                    current_item = self.table.item(row, column)
                    old_value = current_item.text() if current_item else ""

                    self._suppress_table_change = True
                    try:
                        if current_item:
                            current_item.setText(formatted_date)
                            self._mark_cell_pending(row, column)
                        self._pending_updates[(ticket_number, column_name)] = {
                            'old_value': old_value,
                            'new_value': formatted_date,
                        }
                    finally:
                        self._suppress_table_change = False

                    def _save_in_background():
                        try:
                            self._save_table_change(ticket_number, column_name, formatted_date)
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, True))
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"Fehler beim Speichern des Datums: {e}")
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, False, str(e)))

                    threading.Thread(target=_save_in_background, daemon=True).start()
            return
            
        else:
            # ComboBox für andere Spalten
            combo = QComboBox()
            
            # Fülle ComboBox basierend auf Spalte
            if column_name == 'Status':
                combo.addItems(['Open', 'In Progress', 'Completed', 'Waiting for Customer Feedback', 'Shipping'])
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
                # Lade StorageLocations aus DB
                try:
                    locations_query = "SELECT ID, LocationName FROM StorageLocations ORDER BY LocationName"
                    locations_result = self.db_connection.execute_query(locations_query)
                    if locations_result:
                        location_names = [row['LocationName'] for row in locations_result]
                        combo.addItems([''] + location_names)
                        # Mapping für späteren Zugriff
                        combo.setProperty('location_map', {row['LocationName']: row['ID'] for row in locations_result})
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
            if column_name == 'StorageLocation':
                location_map = combo.property('location_map')
                location_id = location_map.get(new_value, None) if location_map else None
                # Wenn leer gewählt, speichere NULL
                if new_value.strip() == '':
                    location_id = None
                # Wenn Wert nicht gefunden, Fehler
                elif location_id is None:
                    self._show_error("Fehler", f"Lagerort nicht gefunden: {new_value}")
                    return
                # Optimistisches Update (UI zeigt Namen, DB speichert ID/NULL)
                ticket_item = self.table.item(row, 0)
                if ticket_item:
                    ticket_number = ticket_item.text()
                    current_item = self.table.item(row, column)
                    old_value = current_item.text() if current_item else ""
                    self._suppress_table_change = True
                    try:
                        if current_item:
                            current_item.setText(new_value)
                            self._mark_cell_pending(row, column)
                        self._pending_updates[(ticket_number, column_name)] = {
                            'old_value': old_value,
                            'new_value': new_value,
                        }
                    finally:
                        self._suppress_table_change = False

                    def _save_in_background():
                        try:
                            self._save_table_change(ticket_number, column_name, location_id)
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, True))
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"Fehler beim Speichern der Dropdown-Änderung: {e}")
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, False, str(e)))

                    threading.Thread(target=_save_in_background, daemon=True).start()
            elif column_name == 'LastHandler':
                # Extrahiere Initials aus dem ausgewählten Handler
                selected_handler = combo.currentText()
                if selected_handler.strip() == '':
                    handler_initials = None
                else:
                    # Extrahiere Initials aus "Name (Initials)" Format
                    import re
                    match = re.search(r'\(([^)]+)\)$', selected_handler)
                    if match:
                        handler_initials = match.group(1)
                    else:
                        handler_initials = selected_handler
                
                # Optimistisches Update (UI zeigt Initialen)
                ticket_item = self.table.item(row, 0)
                if ticket_item:
                    ticket_number = ticket_item.text()
                    display_value = '' if handler_initials is None else handler_initials
                    current_item = self.table.item(row, column)
                    old_value = current_item.text() if current_item else ""

                    self._suppress_table_change = True
                    try:
                        if current_item:
                            current_item.setText(display_value)
                            self._mark_cell_pending(row, column)
                        self._pending_updates[(ticket_number, column_name)] = {
                            'old_value': old_value,
                            'new_value': display_value,
                        }
                    finally:
                        self._suppress_table_change = False

                    def _save_in_background():
                        try:
                            self._save_table_change(ticket_number, column_name, handler_initials)
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, True))
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"Fehler beim Speichern der Dropdown-Änderung: {e}")
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, False, str(e)))

                    threading.Thread(target=_save_in_background, daemon=True).start()
            elif column_name == 'Status':
                # Optimistisches Update für Status
                ticket_item = self.table.item(row, 0)
                if ticket_item:
                    ticket_number = ticket_item.text()
                    current_item = self.table.item(row, column)
                    old_value = current_item.text() if current_item else ""

                    # UI sofort aktualisieren, ohne itemChanged zu triggern
                    self._suppress_table_change = True
                    try:
                        if current_item:
                            current_item.setText(new_value)
                            self._mark_cell_pending(row, column)
                        # Speichere Pending-Info
                        self._pending_updates[(ticket_number, column_name)] = {
                            'old_value': old_value,
                            'new_value': new_value,
                        }
                        # Formatierung (nur betroffene Zeile, ohne teure Duplikatsprüfung)
                        self._apply_row_formatting(row, check_duplicates=False)
                    finally:
                        self._suppress_table_change = False

                    # Speichern im Hintergrund
                    def _save_in_background():
                        try:
                            self._save_table_change(ticket_number, column_name, new_value)
                            # Erfolg: Pending entfernen und Markierung zurücksetzen
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, True))
                        except Exception as e:  # noqa: BLE001
                            logger.error(f"Fehler beim Speichern im Hintergrund: {e}")
                            QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, False, str(e)))

                    threading.Thread(target=_save_in_background, daemon=True).start()
            elif column_name == 'Type':
                # Konvertiere deutsche Anzeige zurück zu englischen Werten
                type_mapping = combo.property('type_mapping')
                if type_mapping:
                    english_value = type_mapping.get(new_value, new_value)
                    ticket_item = self.table.item(row, 0)
                    if ticket_item:
                        ticket_number = ticket_item.text()
                        current_item = self.table.item(row, column)
                        old_value = current_item.text() if current_item else ""

                        self._suppress_table_change = True
                        try:
                            if current_item:
                                current_item.setText(new_value)
                            self._mark_cell_pending(row, column)
                            self._pending_updates[(ticket_number, column_name)] = {
                                'old_value': old_value,
                                'new_value': new_value,
                            }
                            # Formatierung nur für diese Zeile aktualisieren
                            self._apply_row_formatting(row, check_duplicates=False)
                        finally:
                            self._suppress_table_change = False

                        def _save_in_background():
                            try:
                                self._save_table_change(ticket_number, column_name, english_value)
                                QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, True))
                            except Exception as e:  # noqa: BLE001
                                logger.error(f"Fehler beim Speichern der Dropdown-Änderung: {e}")
                                QTimer.singleShot(0, lambda: self._finalize_pending_update(ticket_number, column_name, False, str(e)))

                        threading.Thread(target=_save_in_background, daemon=True).start()

    def _create_new_entry(self) -> None:
        """Fügt eine neue leere Zeile zur Tabelle hinzu (Google Sheets Style)."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return
            
        if self.show_deleted_entries:
            self._show_error("Fehler", "Neue Einträge können nur in der aktiven Ansicht erstellt werden")
            return
        
        # Füge eine neue leere Zeile am Anfang der Tabelle hinzu
        self.table.insertRow(0)
        
        # Erstelle leere Items für alle Spalten
        for col in range(self.table.columnCount()):
            item = QTableWidgetItem("")
            
            # Setze Flags basierend auf Spaltentyp
            header = self.table.horizontalHeader()
            column_name = header.model().headerData(col, Qt.Orientation.Horizontal)
            
            if column_name in ['Status', 'Type', 'StorageLocation', 'LastHandler']:
                # Dropdown-Spalten: Nur Auswahl erlauben
                item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | 
                    Qt.ItemFlag.ItemIsEnabled
                )
            elif column_name in ['EntryDate', 'ExitDate']:
                # Datum-Spalten: Direkte Bearbeitung erlauben
                item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | 
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsEditable
                )
            else:
                # Normale Spalten: Vollständige Bearbeitung erlauben
                item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | 
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsEditable
                )
            
            self.table.setItem(0, col, item)
        
        # Setze Fokus auf die erste Zelle (TicketNumber)
        self.table.setCurrentCell(0, 0)
        self.table.editItem(self.table.item(0, 0))
        
        # Markiere die neue Zeile visuell
        for col in range(self.table.columnCount()):
            item = self.table.item(0, col)
            if item:
                item.setBackground(QColor(255, 255, 220))  # Helles Gelb für neue Zeile
        
        self.status_bar.showMessage("Neue Zeile hinzugefügt - Füllen Sie die Daten aus", 3000)

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

    def _toggle_dark_mode(self) -> None:
        """Schaltet zwischen Dark Mode und Light Mode um."""
        self.dark_mode_enabled = not self.dark_mode_enabled

        if self.dark_mode_enabled:
            self.dark_mode_action.setText("☀️ Light Mode")
            self._apply_dark_theme()
        else:
            self.dark_mode_action.setText("🌙 Dark Mode")
            self._apply_light_theme()

        # Aktualisiere Status
        mode_text = "Dark Mode" if self.dark_mode_enabled else "Light Mode"
        self.status_bar.showMessage(f"Theme gewechselt: {mode_text}", 3000)

    def _apply_dark_theme(self) -> None:
        """Wendet das Dark Theme auf die Anwendung an."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTableWidget {
            background-color: #3c3c3c;
            color: #ffffff;
            gridline-color: #555555;
            selection-background-color: #4a90e2;
        }
        QTableWidget QHeaderView::section {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QLineEdit {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QPushButton {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QStatusBar {
            background-color: #404040;
            color: #ffffff;
            border-top: 1px solid #555555;
        }
        QToolBar {
            background-color: #363636;
            border-bottom: 1px solid #555555;
        }
        QLabel {
            color: #ffffff;
        }
        QMenu {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QMenu::item:selected {
            background-color: #4a90e2;
        }
        """

        # Wende das Stylesheet an
        self.setStyleSheet(dark_stylesheet)

        # Aktualisiere Tabellenfarben für Dark Mode
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #353535;
            }
        """)

    def _apply_light_theme(self) -> None:
        """Wendet das Light Theme auf die Anwendung an."""
        light_stylesheet = """
        QMainWindow {
            background-color: #f0f0f0;
            color: #000000;
        }
        QTableWidget {
            background-color: #ffffff;
            color: #000000;
            gridline-color: #d0d0d0;
            selection-background-color: #4a90e2;
        }
        QTableWidget QHeaderView::section {
            background-color: #e0e0e0;
            color: #000000;
            border: 1px solid #c0c0c0;
        }
        QLineEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #c0c0c0;
        }
        QPushButton {
            background-color: #e0e0e0;
            color: #000000;
            border: 1px solid #c0c0c0;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QStatusBar {
            background-color: #e0e0e0;
            color: #000000;
            border-top: 1px solid #c0c0c0;
        }
        QToolBar {
            background-color: #d0d0d0;
            border-bottom: 1px solid #c0c0c0;
        }
        QLabel {
            color: #000000;
        }
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #c0c0c0;
        }
        QMenu::item:selected {
            background-color: #4a90e2;
        }
        """

        # Wende das Stylesheet an
        self.setStyleSheet(light_stylesheet)

        # Aktualisiere Tabellenfarben für Light Mode
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f9f9f9;
            }
        """)

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

    def _filter_table(self) -> None:
        """Filtert die Tabelle basierend auf der Sucheingabe."""
        search_text = self.search_input.text().lower().strip()
        
        if not search_text:
            # Zeige alle Daten an
            self._restore_original_data()
            return
        
        # Filtere die Daten
        filtered_data = []
        for row_data in self.original_data:
            # Suche in Ticket-Nummer, Auftragsnummer und Produktname
            if (search_text in row_data.get('TicketNumber', '').lower() or
                search_text in row_data.get('OrderNumber', '').lower() or
                search_text in row_data.get('ProductName', '').lower()):
                filtered_data.append(row_data)
        
        # Aktualisiere Tabelle mit gefilterten Daten
        self._populate_table_with_data(filtered_data)
        
        # Aktualisiere Status
        self.status_bar.showMessage(f"Suche: {len(filtered_data)} von {len(self.original_data)} Einträgen gefunden", 3000)

    def _clear_search(self) -> None:
        """Löscht die Sucheingabe und zeigt alle Daten an."""
        self.search_input.clear()
        self._restore_original_data()

    def _restore_original_data(self) -> None:
        """Stellt die ursprünglichen Daten wieder her."""
        if self.original_data:
            self._populate_table_with_data(self.original_data)
            self.status_bar.showMessage(f"Alle {len(self.original_data)} Einträge angezeigt", 3000)

    def _populate_table_with_data(self, data: List[Dict[str, Any]]) -> None:
        if not data:
            self.table.setRowCount(0)
            self.table.setSortingEnabled(True)
            header = self.table.horizontalHeader()
            header.setSectionsClickable(True)
            try:
                header.sortIndicatorChanged.disconnect(self._log_sort)
            except TypeError:
                pass
            header.sortIndicatorChanged.connect(self._log_sort)
            return
        # Entferne alle Signal-Disconnects/Connects hier

        # Bestimme sichtbare Spalten basierend auf Ansicht
        if self.show_deleted_entries:
            visible_columns = [
                'TicketNumber', 'OrderNumber', 'Type', 'EntryDate', 
                'Status', 'ExitDate', 'TrackingNumber', 'IsAmazon',
                'StorageLocation', 'LastHandler', 'DeletedAt', 'DeletedBy'
            ]
        else:
            visible_columns = [
                'TicketNumber', 'OrderNumber', 'Type', 'EntryDate', 
                'Status', 'ExitDate', 'TrackingNumber', 'IsAmazon',
                'StorageLocation', 'LastHandler'
            ]
        
        self.table.setRowCount(len(data))
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
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        self.table.setSortingEnabled(True)
        try:
            header.sortIndicatorChanged.disconnect(self._log_sort)
        except TypeError:
            pass
        header.sortIndicatorChanged.connect(self._log_sort)
        
        # Blockiere Signale während des Füllens der Tabelle
        self.table.blockSignals(True)
        
        for row_idx, row_data in enumerate(data):
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

                # Setze die Flags für alle Items auf voll editierbar (für Sortierbarkeit)
                if key in ['Status', 'Type', 'StorageLocation', 'LastHandler']:
                    item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable |
                        Qt.ItemFlag.ItemIsEnabled
                    )
                elif key in ['EntryDate', 'ExitDate']:
                    # Datum-Spalten: Direkte Bearbeitung erlauben
                    item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable | 
                        Qt.ItemFlag.ItemIsEnabled |
                        Qt.ItemFlag.ItemIsEditable
                    )
                else:
                    item.setFlags(
                        Qt.ItemFlag.ItemIsSelectable |
                        Qt.ItemFlag.ItemIsEnabled |
                        Qt.ItemFlag.ItemIsEditable
                    )

                # Visuelle Indikatoren für gelöschte Einträge
                if self.show_deleted_entries:
                    item.setBackground(Qt.GlobalColor.lightGray)
                    font = item.font()
                    font.setStrikeOut(True)
                    item.setFont(font)
                
                self.table.setItem(row_idx, col_idx, item)
                col_idx += 1
        
        # Signale wieder aktivieren
        self.table.blockSignals(False)
        
        # Spaltenbreiten anpassen
        self.table.resizeColumnsToContents()

        # Qt übernimmt die Sortierung automatisch

    def _apply_conditional_formatting(self) -> None:
        """Wendet bedingte Formatierung basierend auf dem Status an (Google Sheets Style)."""
        try:
            for row in range(self.table.rowCount()):
                # Status-Spalte finden (Spalte 4)
                status_item = self.table.item(row, 4)  # Status ist Spalte 4
                if not status_item:
                    continue
                
                status = status_item.text().strip()
                
                # Google Sheets Farbkodierung:
                # 🟡 Gelb = Offene Fälle
                # 🟢 Grün = Erledigte Fälle  
                # 🔵 Blau = Auf Kundenrückmeldung warten
                # ⚪ Weiß = Standard
                if status == 'Open':
                    # Gelb für offene Fälle (wie Google Sheets)
                    color = QColor(255, 255, 153)  # Google Sheets Gelb
                elif status == 'Waiting for Customer Feedback':
                    # Blau für "auf Kundenrückmeldung warten"
                    color = QColor(173, 216, 230)  # Google Sheets Blau
                elif status == 'Completed':
                    # Grün für erledigte Fälle
                    color = QColor(144, 238, 144)  # Google Sheets Grün
                elif status == 'In Progress':
                    # Helles Blau für in Bearbeitung
                    color = QColor(200, 220, 255)  # Helles Blau
                elif status == 'Shipping':
                    # Dunkles Blau für Shipping (DHL-Label erstellt, unterwegs)
                    color = QColor(100, 150, 255)  # Dunkles Blau
                else:
                    # Standardfarbe für unbekannte Status
                    color = QColor(255, 255, 255)  # Weiß
                
                # Farbe auf alle Zellen der Zeile anwenden
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(color)
                
                # Seriennummer-Duplikat-Erkennung (rote Markierung)
                self._check_duplicate_serial_numbers(row)
                        
        except Exception as e:
            logger.error(f"Fehler bei bedingter Formatierung: {e}")

        # Behalte Pending-Markierungen sicht- und konsistent
        self._reapply_pending_overlays()

    def _apply_row_formatting(self, row: int, check_duplicates: bool = True) -> None:
        """Wendet Formatierung für eine einzelne Zeile an (schneller als Full-Repaint)."""
        try:
            status_item = self.table.item(row, 4)
            status = status_item.text().strip() if status_item else ''
            if status == 'Open':
                color = QColor(255, 255, 153)
            elif status == 'Waiting for Customer Feedback':
                color = QColor(173, 216, 230)
            elif status == 'Completed':
                color = QColor(144, 238, 144)
            elif status == 'In Progress':
                color = QColor(200, 220, 255)
            elif status == 'Shipping':
                color = QColor(100, 150, 255)
            else:
                color = QColor(255, 255, 255)

            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(color)

            if check_duplicates:
                self._check_duplicate_serial_numbers(row)
        except Exception as e:
            logger.error(f"Fehler bei Zeilenformatierung: {e}")

    def _check_duplicate_serial_numbers(self, row: int) -> None:
        """Markiert Seriennummern rot, die bereits mehrfach in der RMA-Tabelle vorkommen."""
        try:
            # Seriennummer-Spalte finden (normalerweise Spalte 3)
            serial_item = self.table.item(row, 3)  # Seriennummer ist Spalte 3
            if not serial_item:
                return
            
            serial_number = serial_item.text().strip()
            if not serial_number:
                return
            
            # Prüfe, ob diese Seriennummer bereits mehrfach existiert
            if self._is_duplicate_serial(serial_number):
                # Rote Hintergrundfarbe für Seriennummer
                serial_item.setBackground(QColor(255, 200, 200))  # Helles Rot
                # Tooltip hinzufügen
                serial_item.setToolTip("⚠️ Seriennummer bereits mehrfach in RMA-Tabelle vorhanden")
                
        except Exception as e:
            logger.error(f"Fehler bei Duplikat-Erkennung: {e}")

    def _is_duplicate_serial(self, serial_number: str) -> bool:
        """Prüft, ob eine Seriennummer bereits mehrfach in der RMA-Tabelle vorkommt."""
        try:
            if not self.db_connection:
                return False
            
            # Query: Zähle Vorkommen dieser Seriennummer
            query = """
                SELECT COUNT(*) as count 
                FROM RMA_Products 
                WHERE SerialNumber = %s AND IsDeleted = FALSE
            """
            results = self.db_connection.execute_query(query, (serial_number,))
            
            if results and len(results) > 0:
                count = results[0].get('count', 0)
                return count > 1  # Mehr als einmal = Duplikat
                
            return False
            
        except Exception as e:
            logger.error(f"Fehler bei Duplikat-Prüfung: {e}")
            return False

    def _create_new_database_entry(self, ticket_number: str) -> None:
        """Erstellt einen neuen Datenbankeintrag für die angegebene Ticket-Nummer."""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Beginne Transaktion
                cursor.execute("START TRANSACTION")
                
                try:
                    # Erstelle RMA_Cases Eintrag
                    cursor.execute("""
                        INSERT INTO RMA_Cases (TicketNumber, OrderNumber, EntryDate, Status, Type) 
                        VALUES (%s, %s, CURDATE(), 'Open', 'repair')
                    """, (ticket_number, ''))
                    
                    # Erstelle RMA_RepairDetails Eintrag
                    cursor.execute("""
                        INSERT INTO RMA_RepairDetails (TicketNumber, OrderNumber, LastHandler) 
                        VALUES (%s, %s, %s)
                    """, (ticket_number, '', self.current_user))
                    
                    # Commit Transaktion
                    cursor.execute("COMMIT")
                    logger.info(f"Neuer RMA-Eintrag erstellt: {ticket_number}")
                    
                except Exception as e:
                    # Rollback bei Fehler
                    cursor.execute("ROLLBACK")
                    raise e
                    
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des neuen Eintrags: {e}")
            raise e

    def _table_key_press_event(self, event: QKeyEvent) -> None:
        """Behandelt Tastatureingaben in der Tabelle."""
        if event.key() in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]:
            # Aktuelle Zelle löschen
            current_item = self.table.currentItem()
            if current_item:
                # Bestimme welche Spalte geändert wurde
                row = current_item.row()
                column = current_item.column()
                header = self.table.horizontalHeader()
                column_name = header.model().headerData(column, Qt.Orientation.Horizontal)
                
                # Hole Ticket-Nummer der Zeile
                ticket_item = self.table.item(row, 0)  # TicketNumber ist die erste Spalte
                if ticket_item:
                    ticket_number = ticket_item.text()
                    
                    # Zelle leeren
                    current_item.setText("")
                    
                    # In Datenbank speichern (leerer Wert)
                    logger.info(f"Zelle gelöscht: {ticket_number}, Spalte: {column_name}")
                    self._save_table_change(ticket_number, column_name, "")
                    
                    # Event als behandelt markieren
                    event.accept()
                    return
        
        # Standard-Verhalten für andere Tasten
        QTableWidget.keyPressEvent(self.table, event)
    
    def _log_sort(self, logical_index: int, order: Qt.SortOrder) -> None:
        """Loggt jeden Sortierwechsel und führt die Sortierung durch."""
        logger.info(f"Sortierung geändert - Spalte: {logical_index}, Richtung: {order}")
        
        # Sortierung durchführen
        self.table.sortItems(logical_index, order)
        
        # Sortierindikator setzen
        header = self.table.horizontalHeader()
        header.setSortIndicator(logical_index, order)

    # ===========================
    # Optimistic-UI Hilfsfunktionen
    # ===========================

    def _rebuild_row_index_by_ticket(self) -> None:
        """Erstellt ein Mapping von TicketNumber auf Tabellenzeile."""
        self._row_by_ticket.clear()
        for row in range(self.table.rowCount()):
            ticket_item = self.table.item(row, 0)
            if ticket_item:
                self._row_by_ticket[ticket_item.text()] = row

    def _get_column_index_by_name(self, column_name: str) -> int:
        """Gibt den Spaltenindex anhand des Spaltennamens zurück oder -1."""
        header = self.table.horizontalHeader()
        for idx in range(self.table.columnCount()):
            name = header.model().headerData(idx, Qt.Orientation.Horizontal)
            if name == column_name:
                return idx
        return -1

    def _mark_cell_pending(self, row: int, column: int) -> None:
        """Markiert eine Zelle als 'pending' (optische Kennzeichnung)."""
        item = self.table.item(row, column)
        if not item:
            return
        font = item.font()
        font.setItalic(True)
        item.setFont(font)
        item.setForeground(QColor(90, 90, 90))
        item.setToolTip("Änderung wird synchronisiert …")

    def _clear_cell_pending(self, row: int, column: int) -> None:
        """Entfernt die 'pending' Kennzeichnung einer Zelle."""
        item = self.table.item(row, column)
        if not item:
            return
        font = item.font()
        font.setItalic(False)
        item.setFont(font)
        item.setForeground(QColor(0, 0, 0))
        item.setToolTip("")

    def _finalize_pending_update(self, ticket_number: str, column_name: str, success: bool, error_message: Optional[str] = None) -> None:
        """Finalisiert eine ausstehende Änderung: entfernt Pending oder macht Rollback."""
        key = (ticket_number, column_name)
        pending = self._pending_updates.get(key)
        col_idx = self._get_column_index_by_name(column_name)
        row_idx = self._row_by_ticket.get(ticket_number, -1)

        if row_idx >= 0 and col_idx >= 0:
            if success:
                # Erfolg: Pending-Markierung entfernen
                self._clear_cell_pending(row_idx, col_idx)
                self.status_bar.showMessage("Änderung gespeichert", 2000)
                # Eintrag aus Pending entfernen
                if key in self._pending_updates:
                    del self._pending_updates[key]
            else:
                # Fehler: Rollback zum alten Wert, Pending entfernen
                if pending is not None:
                    old_value = pending.get('old_value', '')
                    self._suppress_table_change = True
                    try:
                        item = self.table.item(row_idx, col_idx)
                        if item:
                            item.setText(old_value)
                    finally:
                        self._suppress_table_change = False
                self._clear_cell_pending(row_idx, col_idx)
                if key in self._pending_updates:
                    del self._pending_updates[key]
                if error_message:
                    self._show_error("Fehler", f"Änderung konnte nicht gespeichert werden: {error_message}")

        # Nach Finalisierung Pending erneut anwenden, falls weitere Einträge existieren
        self._reapply_pending_overlays()

    def _reapply_pending_overlays(self) -> None:
        """Wendet ausstehende Änderungen erneut an (z. B. nach Reload/Formatierung)."""
        if not self._pending_updates:
            return
        for (ticket_number, column_name), info in list(self._pending_updates.items()):
            row_idx = self._row_by_ticket.get(ticket_number, -1)
            col_idx = self._get_column_index_by_name(column_name)
            if row_idx < 0 or col_idx < 0:
                continue
            new_value = str(info.get('new_value', '') or '')
            item = self.table.item(row_idx, col_idx)
            if not item:
                continue
            # Wenn der aktuelle (Server-)Wert bereits dem neuen Wert entspricht,
            # ist die Synchronisierung abgeschlossen -> Pending entfernen
            current_text = item.text()
            if current_text == new_value:
                self._finalize_pending_update(ticket_number, column_name, True)
                continue
            # Setze Wert ohne itemChanged auszulösen
            self._suppress_table_change = True
            try:
                item.setText(new_value)
            finally:
                self._suppress_table_change = False
            # Stelle Pending-Optik sicher
            self._mark_cell_pending(row_idx, col_idx)

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