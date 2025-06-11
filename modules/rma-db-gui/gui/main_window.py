"""Main window for the RMA Database GUI.

This module provides the main application window with a modern, user-friendly
interface for managing RMA database entries.
"""

from __future__ import annotations

import sys
from typing import Optional, List

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
        self._setup_ui()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_connections()

        # Initialize database connection
        self.db_connection: Optional[DatabaseConnection] = None

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
        self.password_input.setPlaceholderText("Enter KeePass master password")
        self.password_input.setFont(QFont("Segoe UI", 10))
        self.password_input.setMinimumWidth(200)
        password_layout.addWidget(self.password_input)

        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.connect_button.setFont(QFont("Segoe UI", 10))
        self.connect_button.setMinimumWidth(100)
        password_layout.addWidget(self.connect_button)

        # Add password widget to main layout
        main_layout.addWidget(password_widget)

        # Create table
        self.table = QTableWidget()
        self.table.setFont(QFont("Segoe UI", 10))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table)

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
        """Löscht die ausgewählten RMA-Einträge."""
        if not self.db_connection:
            self._show_error("Fehler", "Keine Datenbankverbindung")
            return

        rma_numbers = self._get_selected_rma_numbers()
        if not rma_numbers:
            self._show_error("Fehler", "Bitte wählen Sie mindestens einen Eintrag aus")
            return

        # Bestätigungsdialog anzeigen
        dialog = DeleteConfirmationDialog(self, rma_numbers)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Beginne Transaktion
                cursor.execute("START TRANSACTION")
                
                try:
                    # Lösche zuerst abhängige Daten
                    if dialog.delete_attachments:
                        cursor.execute(
                            "DELETE a FROM attachments a "
                            "INNER JOIN rma_requests r ON a.rma_request_id = r.id "
                            "WHERE r.rma_number IN %s",
                            (rma_numbers,)
                        )
                    
                    if dialog.delete_shipping:
                        cursor.execute(
                            "DELETE s FROM shipping s "
                            "INNER JOIN rma_requests r ON s.rma_request_id = r.id "
                            "WHERE r.rma_number IN %s",
                            (rma_numbers,)
                        )
                    
                    # Lösche RMA-Einträge
                    cursor.execute(
                        "DELETE FROM rma_requests WHERE rma_number IN %s",
                        (rma_numbers,)
                    )
                    
                    # Commit Transaktion
                    cursor.execute("COMMIT")
                    
                    self._show_success(
                        "Erfolg",
                        f"{len(rma_numbers)} RMA-Einträge wurden gelöscht"
                    )
                    
                    # Tabelle aktualisieren
                    self.load_rma_data()
                    
                except Exception as e:
                    # Bei Fehler Rollback
                    cursor.execute("ROLLBACK")
                    raise e
                    
        except DatabaseConnectionError as e:
            self._show_error("Datenbankfehler", str(e))
        except Exception as e:
            logger.exception("Fehler beim Löschen der Einträge")
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

    def load_rma_data(self) -> None:
        """Load RMA data from the database and display it in the table."""
        if not self.db_connection:
            return

        try:
            # Execute query to get RMA data
            results = self.db_connection.execute_query("SELECT * FROM RMA_Cases")

            if not results:
                self.table.setRowCount(0)
                self.status_bar.showMessage("No RMA data found", 5000)
                return

            # Set up table
            self.table.setRowCount(len(results))
            self.table.setColumnCount(len(results[0]))
            self.table.setHorizontalHeaderLabels(results[0].keys())

            # Fill table with data
            for row_idx, row_data in enumerate(results):
                for col_idx, value in enumerate(row_data.values()):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row_idx, col_idx, item)

            # Adjust column widths
            self.table.resizeColumnsToContents()
            self.status_bar.showMessage(f"Loaded {len(results)} RMA entries", 5000)

        except DatabaseConnectionError as e:
            self._show_error("Database Error", str(e))
        except Exception as e:
            logger.exception("Unexpected error while loading RMA data")
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