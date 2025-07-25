"""RMA-Tool - Zentrale Hauptanwendung.

Diese Datei dient als Einstiegspunkt für das gesamte RMA-Tool.
Sie ermöglicht die Auswahl zwischen verschiedenen Modulen.
"""

import sys
import os
from pathlib import Path
from typing import Optional

# PyQt6 Imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QWidget, QMessageBox, QDialog, QFrame
from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog

)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap

# Zentrale Infrastruktur importieren
from shared.credentials import CentralKeePassHandler, CentralLoginWindow
from shared.credentials.credential_cache import (
    initialize_credential_cache, get_credential_cache
)
from shared.credentials.credential_manager import CredentialManager
from shared.utils.logger import setup_logger, LogBlock
from shared.utils.error_handler import ErrorHandler
from shared.config.settings import Settings


class ModuleSelector(QMainWindow):
    """Hauptfenster für die Modulauswahl."""

    def __init__(self):
        """Initialisiere das Hauptfenster."""
        super().__init__()
        
        # Zentrale Komponenten initialisieren
        self.settings = Settings()
        self.logger = setup_logger("RMA-Tool.Main")
        self.error_handler = ErrorHandler()
        self.kp_handler: Optional[CentralKeePassHandler] = None
        self.credential_cache = None
        self.credential_manager: Optional[CredentialManager] = None

        # Fenster-Einstellungen anwenden
        window_settings = self.settings.get_window_settings()
        self.setWindowTitle("RMA-Tool - Modulauswahl")
        self.setGeometry(100, 100, window_settings.get("width", 600), 
                        window_settings.get("height", 700))
        self.setMinimumSize(window_settings.get("min_width", 600),
                           window_settings.get("min_height", 700))

        # Erst authentifizieren, dann UI anzeigen
        if self._authenticate():
            self._setup_ui()
            self._update_status()
            if window_settings.get("center_on_startup", True):
                self._center_window()
        else:
            sys.exit(1)

    def _setup_ui(self):
        """Benutzeroberfläche einrichten."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Hauptlayout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Titel
        title_label = QLabel("RMA-Tool")
        title_label.setProperty("class", "title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Untertitel
        subtitle_label = QLabel("Wählen Sie ein Modul aus:")
        subtitle_label.setProperty("class", "subtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        main_layout.addWidget(subtitle_label)

        # Modul-Buttons
        self._create_module_buttons(main_layout)

        # Status-Bereich
        self._create_status_section(main_layout)

        main_layout.addStretch()

    def _create_module_buttons(self, parent_layout):
        """Modul-Buttons erstellen."""
        # Button-Container
        button_frame = QFrame()
        button_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        button_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
            }
        """)

        button_layout = QVBoxLayout(button_frame)
        button_layout.setSpacing(15)

        # Module aus Einstellungen laden
        modules = self.settings.get("modules", {})
        
        # DHL Label Tool Button
        if modules.get("dhl_label_tool", {}).get("enabled", True):
            dhl_button = self._create_module_button(
                "DHL Label Tool",
                "DHL-Versandlabels erstellen und verwalten",
                "📦"
            )
            dhl_button.clicked.connect(self._start_dhl_label_tool)
            button_layout.addWidget(dhl_button)

        # RMA Database GUI Button
        if modules.get("rma_db_gui", {}).get("enabled", True):
            rma_button = self._create_module_button(
                "RMA Database GUI",
                "RMA-Fälle verwalten und Bestellungen erfassen",
                "🗄️"
            )
            rma_button.clicked.connect(self._start_rma_database_gui)
            button_layout.addWidget(rma_button)

        parent_layout.addWidget(button_frame)

    def _create_module_button(self, title: str, description: str, 
                            icon: str) -> QPushButton:
        """Einen Modul-Button erstellen."""
        button = QPushButton(f"{icon} {title}\n{description}")
        button.setFixedHeight(80)
        button.setProperty("class", "module-button")

        return button

    def _create_status_section(self, parent_layout):
        """Status-Bereich erstellen."""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 15px;
            }
        """)

        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(10)

        # Status-Titel
        status_title = QLabel("System-Status")
        status_title.setStyleSheet("font-weight: bold; color: #495057;")
        status_layout.addWidget(status_title)

        # KeePass-Status
        self.kp_status_label = QLabel("🔴 KeePass: Nicht verbunden")
        self.kp_status_label.setStyleSheet("color: #dc3545;")
        status_layout.addWidget(self.kp_status_label)

        # Credential Cache Status
        self.cache_status_label = QLabel("🔴 Credential Cache: Nicht aktiv")
        self.cache_status_label.setStyleSheet("color: #dc3545;")
        status_layout.addWidget(self.cache_status_label)

        # Log-Status
        self.log_status_label = QLabel("🟢 Logging: Aktiv")
        self.log_status_label.setStyleSheet("color: #28a745;")
        status_layout.addWidget(self.log_status_label)

        parent_layout.addWidget(status_frame)

    def _center_window(self):
        """Fenster zentrieren."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _update_status(self):
        """Status-Anzeige aktualisieren."""
        # KeePass Status
        if self.kp_handler and self.kp_handler.is_database_open():
            self.kp_status_label.setText("🟢 KeePass: Verbunden")
            self.kp_status_label.setStyleSheet("color: #28a745;")
        else:
            self.kp_status_label.setText("🔴 KeePass: Nicht verbunden")
            self.kp_status_label.setStyleSheet("color: #dc3545;")

        # Credential Cache Status
        if self.credential_cache and self.credential_cache.has_valid_session():
            cache_stats = self.credential_cache.get_cache_stats()
            self.cache_status_label.setText(
                f"🟢 Credential Cache: Aktiv "
                f"({cache_stats['valid_credentials']} Credentials)"
            )
            self.cache_status_label.setStyleSheet("color: #28a745;")
        else:
            self.cache_status_label.setText("🔴 Credential Cache: Nicht aktiv")
            self.cache_status_label.setStyleSheet("color: #dc3545;")

    def _authenticate(self) -> bool:
        """KeePass-Authentifizierung durchführen."""
        with LogBlock(self.logger) as log:
            try:
                # Credential Cache initialisieren
                self.credential_cache = initialize_credential_cache()
                log("Credential cache initialized")

                if not self.kp_handler:
                    self.kp_handler = CentralKeePassHandler()
                    log("Central KeePass handler initialized")

                if not self.kp_handler.is_database_open():
                    log.section("Login Dialog")
                    login_window = CentralLoginWindow(self.kp_handler)
                    if login_window.exec() != QDialog.DialogCode.Accepted:
                        log("Login cancelled by user")
                        return False

                    # Benutzer-Credentials aus dem Login-Fenster extrahieren
                    credentials = login_window.get_credentials()
                    if credentials:
                        initials, master_pw = credentials
                        self.kp_handler.set_user_credentials(initials, master_pw)
                        log(f"User credentials stored for: {initials}")

                    log("Login successful")

                # Credential Manager initialisieren
                self.credential_manager = CredentialManager(self.kp_handler)
                log("Credential manager initialized")

                return True

            except Exception as e:
                self.error_handler.handle_credential_error("KeePass", e)
                return False

    def _start_dhl_label_tool(self):
        """DHL Label Tool starten."""
        with LogBlock(self.logger) as log:
            try:
                log.section("Module Import")
                # Importiere das DHL-Tool direkt
                import sys
                import os
                dhl_path = os.path.join(os.path.dirname(__file__), 
                                      "modules", "dhl_label_tool")
                sys.path.insert(0, dhl_path)
                from main import main as dhl_main

                log.section("Module Execution")
                # Starte das DHL-Tool direkt
                dhl_main()
                log("DHL Label Tool erfolgreich gestartet")

            except ImportError as e:
                self.error_handler.handle_error(
                    e, "Modul-Fehler", True
                )
            except Exception as e:
                self.error_handler.handle_error(
                    e, "Ausführungsfehler", True
                )

    def _start_rma_database_gui(self):
        """RMA Database GUI starten."""
        with LogBlock(self.logger) as log:
            try:
                log.section("Module Import")
                from modules.rma_db_gui.gui.main_window import MainWindow

                log.section("Module Execution")
                # Starte das RMA Database GUI Modul ohne Parameter
                rma_window = MainWindow()
                rma_window.show()
                log("RMA Database GUI erfolgreich gestartet")

            except ImportError as e:
                self.error_handler.handle_error(
                    e, "Modul-Fehler", True
                )
            except Exception as e:
                self.error_handler.handle_error(
                    e, "Ausführungsfehler", True
                )


def main():
    """Hauptfunktion der Anwendung."""
    logger = setup_logger("RMA-Tool.Main")
    error_handler = ErrorHandler()
    
    with LogBlock(logger) as log:
        try:
            log.section("Application Initialization")

            # QApplication erstellen
            app = QApplication(sys.argv)
            app.setApplicationName("RMA-Tool")
            app.setApplicationVersion("1.0.0")

            # Globales Stylesheet laden
            style_path = Path(__file__).parent / "global_style.qss"
            if style_path.exists():
                with open(style_path, "r", encoding="utf-8") as f:
                    app.setStyleSheet(f.read())
                    log("Global stylesheet loaded")

            # Hauptfenster erstellen und anzeigen
            log.section("Main Window")
            window = ModuleSelector()
            window.show()  # Fenster anzeigen
            log("Main window displayed")

            # Event-Loop starten
            log.section("Application Loop")
            sys.exit(app.exec())

        except Exception as e:
            error_handler.handle_unknown_error(e, "RMA-Tool Startup")


if __name__ == "__main__":
    main() 