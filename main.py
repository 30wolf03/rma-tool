"""RMA-Tool - Zentrale Hauptanwendung.

Diese Datei dient als Einstiegspunkt für das gesamte RMA-Tool.
Sie ermöglicht die Auswahl zwischen verschiedenen Modulen.
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Zentrale Infrastruktur importieren
from shared.credentials import CentralKeePassHandler, CentralLoginWindow
from shared.credentials.credential_cache import initialize_credential_cache, get_credential_cache
from shared.utils.unified_logger import initialize_logging, get_logger, log_block
from shared.utils.enhanced_logging import (
    setup_enhanced_logging, 
    LoggingMessageBox, 
    log_error_and_show_dialog
)
from shared.utils.terminal_mirror import create_terminal_mirror
from shared.utils.updater import check_and_update_on_startup, GitUpdater

# PySide6 Imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QWidget, QMessageBox, QDialog, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QFont, QPixmap


class LogWindow(QMainWindow):
    """Separates Fenster für Logging-Ausgabe."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("RMA-Tool - System-Logs")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 500)
        
        # Terminal-Mirror Widget erstellen und als zentrales Widget setzen
        self.terminal_mirror = create_terminal_mirror(self)
        self.setCentralWidget(self.terminal_mirror)
        
        # Fenster zentrieren
        self._center_window()
        
    def _center_window(self):
        """Fenster zentrieren."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def closeEvent(self, event):
        """Beim Schließen nur verstecken und Parent-Button zurücksetzen."""
        self.hide()
        # Parent-Button zurücksetzen
        if self.parent and hasattr(self.parent, 'log_toggle_button'):
            self.parent.log_toggle_button.setChecked(False)
        event.ignore()


class ModuleSelector(QMainWindow):
    """Hauptfenster für die Modulauswahl."""
    
    def __init__(self):
        super().__init__()
        # Einheitliches Logging-System verwenden
        self.logger = get_logger("Main")
        self.kp_handler: Optional[CentralKeePassHandler] = None
        self.credential_cache = None
        self.log_window: Optional[LogWindow] = None
        self.rma_window = None  # Referenz auf das RMA Database GUI Fenster
        
        self.setWindowTitle("RMA-Tool - Modulauswahl")
        self.setGeometry(100, 100, 800, 500)
        self.setMinimumSize(800, 500)
        
        # Erst authentifizieren, dann UI anzeigen
        if self._authenticate():
            self._setup_ui()
            self._update_status()  # Status nach UI-Erstellung aktualisieren
            self._center_window()
            # RMA-DB-GUI im Hintergrund vorladen, damit das erste Öffnen instant ist
            QTimer.singleShot(0, self._preload_rma_database_gui)
        else:
            # Bei fehlgeschlagener Authentifizierung beenden
            sys.exit(1)
        
    def _setup_ui(self):
        """Benutzeroberfläche einrichten."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Hauptlayout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header-Bereich mit Titel, Status-Lämpchen und Log-Toggle
        self._create_header_section(main_layout)
        
        # Modul-Buttons
        self._create_module_buttons(main_layout)
        
        # Stretch für bessere Verteilung
        main_layout.addStretch()
        
    def _create_header_section(self, parent_layout):
        """Header mit Titel, Status-Lämpchen und Log-Toggle erstellen."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        # Titel-Bereich
        title_layout = QVBoxLayout()
        
        title_label = QLabel("RMA-Tool")
        title_label.setProperty("class", "title")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #212529; margin-bottom: 5px;")
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Wählen Sie ein Modul aus")
        subtitle_label.setProperty("class", "subtitle")
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #6c757d;")
        title_layout.addWidget(subtitle_label)
        
        # Anzeige des eingeloggten Nutzers
        if self.kp_handler:
            initials = self.kp_handler.get_user_initials()
            if initials:
                user_label = QLabel(f"Eingeloggt als: {initials}")
                user_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 10px;")
                title_layout.addWidget(user_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Status-Lämpchen
        self._create_status_lights(header_layout)
        
        # Update-Button
        self.update_button = QPushButton("🔄 Update")
        self.update_button.setFixedSize(80, 30)
        self.update_button.clicked.connect(self._check_for_updates)
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        header_layout.addWidget(self.update_button)

        # Log-Toggle Button
        self.log_toggle_button = QPushButton("📋 Logs")
        self.log_toggle_button.setCheckable(True)
        self.log_toggle_button.setFixedSize(80, 30)
        self.log_toggle_button.clicked.connect(self._toggle_log_window)
        self.log_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:checked {
                background-color: #28a745;
            }
        """)
        header_layout.addWidget(self.log_toggle_button)
        
        parent_layout.addWidget(header_frame)
        
    def _create_status_lights(self, parent_layout):
        """Kleine Status-Lämpchen erstellen."""
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)
        
        # KeePass Status-Lämpchen
        self.kp_status_light = self._create_status_light("#dc3545", "KeePass: Nicht verbunden")
        status_layout.addWidget(self.kp_status_light)
        
        # Credential Cache Status-Lämpchen
        self.cache_status_light = self._create_status_light("#dc3545", "Credential Cache: Nicht aktiv")
        status_layout.addWidget(self.cache_status_light)
        
        # Log-Status-Lämpchen
        self.log_status_light = self._create_status_light("#28a745", "Logging: Aktiv")
        status_layout.addWidget(self.log_status_light)
        
        parent_layout.addLayout(status_layout)
        
    def _create_status_light(self, color: str, tooltip: str) -> QLabel:
        """Ein einzelnes Status-Lämpchen erstellen."""
        light = QLabel()
        light.setFixedSize(12, 12)
        light.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 6px;
                border: 1px solid #dee2e6;
            }}
        """)
        light.setToolTip(tooltip)
        return light
        
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
        
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(20)
        
        # DHL Label Tool Button
        dhl_button = self._create_module_button(
            "DHL Label Tool",
            "DHL-Versandlabels erstellen und verwalten",
            "📦"
        )
        dhl_button.clicked.connect(self._start_dhl_label_tool)
        button_layout.addWidget(dhl_button)
        
        # RMA Database GUI Button
        rma_button = self._create_module_button(
            "RMA Database GUI",
            "RMA-Fälle verwalten und Bestellungen erfassen",
            "🗄️"
        )
        rma_button.clicked.connect(self._start_rma_database_gui)
        button_layout.addWidget(rma_button)

        parent_layout.addWidget(button_frame)
        
    def _create_module_button(self, title: str, description: str, icon: str) -> QPushButton:
        """Einen Modul-Button erstellen."""
        button = QPushButton(f"{icon} {title}\n{description}")
        button.setFixedHeight(80)
        button.setProperty("class", "module-button")
        
        return button
        
    def _toggle_log_window(self):
        """Log-Fenster ein-/ausblenden."""
        if not self.log_window:
            self.log_window = LogWindow(self)

        if self.log_toggle_button.isChecked():
            self.log_window.show()
            self.log_toggle_button.setText("📋 Logs")
        else:
            self.log_window.hide()
            self.log_toggle_button.setText("📋 Logs")

    def _check_for_updates(self):
        """Manueller Update-Check."""
        with log_block("Manual Update Check") as log:
            try:
                log("Manual update check triggered")

                # Updater initialisieren
                updater = GitUpdater(self)

                # Update-Info abrufen
                update_info = updater.check_for_updates()

                if not update_info.has_updates:
                    LoggingMessageBox.information(
                        self,
                        "Keine Updates",
                        "Das System ist bereits auf dem neuesten Stand."
                    )
                    return

                # Update-Benachrichtigung anzeigen
                should_update = updater.show_update_notification(update_info)

                if should_update:
                    success, message = updater.perform_update()
                    if success:
                        LoggingMessageBox.information(
                            self,
                            "Update erfolgreich",
                            "Das System wurde aktualisiert und muss neu gestartet werden."
                        )
                        # Anwendung beenden für Neustart
                        QApplication.quit()
                    else:
                        LoggingMessageBox.warning(
                            self,
                            "Update fehlgeschlagen",
                            f"Update konnte nicht installiert werden: {message}"
                        )

            except Exception as e:
                log(f"Update check failed: {str(e)}")
                LoggingMessageBox.critical(
                    self,
                    "Update-Fehler",
                    f"Fehler beim Update-Check: {str(e)}"
                )
        
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
            self.kp_status_light.setStyleSheet("""
                QLabel {
                    background-color: #28a745;
                    border-radius: 6px;
                    border: 1px solid #dee2e6;
                }
            """)
            self.kp_status_light.setToolTip("KeePass: Verbunden")
        else:
            self.kp_status_light.setStyleSheet("""
                QLabel {
                    background-color: #dc3545;
                    border-radius: 6px;
                    border: 1px solid #dee2e6;
                }
            """)
            self.kp_status_light.setToolTip("KeePass: Nicht verbunden")
        
        # Credential Cache Status
        if self.credential_cache and self.credential_cache.has_valid_session():
            cache_stats = self.credential_cache.get_cache_stats()
            self.cache_status_light.setStyleSheet("""
                QLabel {
                    background-color: #28a745;
                    border-radius: 6px;
                    border: 1px solid #dee2e6;
                }
            """)
            self.cache_status_light.setToolTip(f"Credential Cache: Aktiv ({cache_stats['valid_credentials']} Credentials)")
        else:
            self.cache_status_light.setStyleSheet("""
                QLabel {
                    background-color: #dc3545;
                    border-radius: 6px;
                    border: 1px solid #dee2e6;
                }
            """)
            self.cache_status_light.setToolTip("Credential Cache: Nicht aktiv")
            
        # Log-Status bleibt immer grün
        self.log_status_light.setStyleSheet("""
            QLabel {
                background-color: #28a745;
                border-radius: 6px;
                border: 1px solid #dee2e6;
            }
        """)
        self.log_status_light.setToolTip("Logging: Aktiv")
            
    def _authenticate(self) -> bool:
        """KeePass-Authentifizierung durchführen."""
        with log_block("Authentifizierung") as log:
            try:
                # Credential Cache initialisieren
                self.credential_cache = initialize_credential_cache()
                log("Credential cache initialized")
                
                if not self.kp_handler:
                    self.kp_handler = CentralKeePassHandler()
                    log("Central KeePass handler initialized")
                
                if not self.kp_handler.is_database_open():
                    log("Login Dialog")
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
                
                return True
                
            except Exception as e:
                log(f"Authentication failed: {str(e)}")
                log_error_and_show_dialog(
                    e,
                    "Authentifizierungsfehler",
                    f"Fehler bei der KeePass-Authentifizierung:\n{str(e)}",
                    "Authentication"
                )
                return False
                
    def _start_dhl_label_tool(self):
        """DHL Label Tool starten."""
        with log_block("DHL Label Tool Start") as log:
            try:
                log("Module Import")
                # Importiere das DHL-Tool direkt
                import sys
                import os
                dhl_path = os.path.join(os.path.dirname(__file__), "modules", "dhl_label_tool")
                sys.path.insert(0, dhl_path)
                from main import main as dhl_main
                
                log("Module Execution")
                # Starte das DHL-Tool direkt
                dhl_main()
                log("DHL Label Tool erfolgreich gestartet")
                
            except ImportError as e:
                log(f"Import error: {str(e)}")
                log_error_and_show_dialog(
                    e,
                    "Modul-Fehler",
                    f"Fehler beim Laden des DHL Label Tool Moduls:\n{str(e)}",
                    "ModuleLoader"
                )
            except Exception as e:
                log(f"Module execution error: {str(e)}")
                log_error_and_show_dialog(
                    e,
                    "Ausführungsfehler",
                    f"Fehler beim Starten des DHL Label Tools:\n{str(e)}",
                    "ModuleExecution"
                )
                
    def _start_rma_database_gui(self):
        """RMA Database GUI starten oder wieder anzeigen."""
        with log_block("RMA Database GUI Start") as log:
            try:
                log("Module Import")
                from modules.rma_db_gui.gui.main_window import MainWindow

                log("Module Execution")
                # Prüfe, ob das Fenster schon existiert
                if self.rma_window is not None:
                    self.rma_window.show()
                    self.rma_window.raise_()
                    self.rma_window.activateWindow()
                    log("RMA Database GUI wieder angezeigt")
                else:
                    # Initialen des eingeloggten Nutzers holen
                    initials = None
                    if self.kp_handler and hasattr(self.kp_handler, 'get_user_initials'):
                        initials = self.kp_handler.get_user_initials()
                    if not initials and hasattr(self.kp_handler, 'user_initials'):
                        initials = self.kp_handler.user_initials
                    if not initials:
                        initials = "MWO"
                    self.rma_window = MainWindow(current_user=initials)
                    self.rma_window.show()
                    # Wenn das Fenster geschlossen wird, Referenz löschen und Logging
                    def on_close(event):
                        log("RMA Database GUI wurde geschlossen (versteckt)")
                        self.rma_window.hide()
                        event.ignore()
                    self.rma_window.closeEvent = on_close
                    log("RMA Database GUI erfolgreich gestartet")

            except ImportError as e:
                log(f"Import error: {str(e)}")
                log_error_and_show_dialog(
                    e,
                    "Modul-Fehler",
                    f"Fehler beim Laden des RMA Database GUI Moduls:\n{str(e)}",
                    "ModuleLoader"
                )
            except Exception as e:
                log(f"Module execution error: {str(e)}")
                log_error_and_show_dialog(
                    e,
                    "Ausführungsfehler",
                    f"Fehler beim Starten der RMA Database GUI:\n{str(e)}",
                    "ModuleExecution"
                )


    def _preload_rma_database_gui(self):
        """Lädt die RMA Database GUI unsichtbar vor, um das erste Öffnen zu beschleunigen."""
        try:
            if self.rma_window is not None:
                return
            # Import hier, um Startfehler klar zu loggen
            from modules.rma_db_gui.gui.main_window import MainWindow

            # Initialen des eingeloggten Nutzers holen (wie im Start-Flow)
            initials = None
            if self.kp_handler and hasattr(self.kp_handler, 'get_user_initials'):
                initials = self.kp_handler.get_user_initials()
            if not initials and hasattr(self.kp_handler, 'user_initials'):
                initials = self.kp_handler.user_initials
            if not initials:
                initials = "MWO"

            # Fenster erstellen, aber nicht anzeigen
            self.rma_window = MainWindow(current_user=initials)

            # closeEvent so setzen, dass es immer nur versteckt wird
            def on_close(event):
                self.logger.info("RMA Database GUI wurde geschlossen (versteckt)")
                self.rma_window.hide()
                event.ignore()
            self.rma_window.closeEvent = on_close

            # Nicht anzeigen – nur vorbereiten (Daten laden, Timer initialisieren)
            self.logger.info("RMA Database GUI vorab geladen (versteckt)")
        except Exception as e:
            self.logger.error(f"Fehler beim Vorladen der RMA Database GUI: {e}")

def main():
    """Hauptfunktion der Anwendung."""
    # Einheitliches Logging-System initialisieren
    initialize_logging(
        log_level="INFO",
        log_dir="logs",
        app_name="RMA-Tool",
        enable_console=True,
        enable_file=True,
        enable_gui=False  # Wird später über Terminal-Mirror aktiviert
    )
    
    with log_block("Application Initialization") as log:
        try:
            # Enhanced logging system initialisieren
            setup_enhanced_logging()
            log("Enhanced logging system initialized")
            
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
            
            # Update-Check durchführen
            log("Update Check")
            should_continue = check_and_update_on_startup()
            if not should_continue:
                log("Update installed, restart required")
                return  # Exit if update was installed

            # Hauptfenster erstellen und anzeigen
            log("Main Window")
            window = ModuleSelector()
            window.show()  # Fenster anzeigen
            log("Main window displayed")
            
            # Event-Loop starten
            log("Application Loop")
            sys.exit(app.exec())
            
        except Exception as e:
            log(f"Error in RMA-Tool Startup: {e}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main() 