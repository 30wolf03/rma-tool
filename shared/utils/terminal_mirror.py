"""Terminal-Spiegelung für die RMA-Tool Anwendung.

Dieses Modul leitet stdout/stderr in ein GUI-Widget um und integriert
sich mit dem einheitlichen Logging-System.
"""

import sys
from io import StringIO
from typing import Optional
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor

from .unified_logger import get_logger, UnifiedLogger


class StreamRedirector(StringIO):
    """Leitet stdout/stderr in ein QTextEdit-Widget um."""
    
    def __init__(self, text_widget: QTextEdit, stream_name: str = "stdout"):
        super().__init__()
        self.text_widget = text_widget
        self.stream_name = stream_name

    def write(self, text):
        if text:
            # Füge Stream-Name als Präfix hinzu
            if self.stream_name == "stderr":
                formatted_text = f"[ERROR] {text}"
            else:
                formatted_text = f"[OUT] {text}"
            
            # Nur in das GUI schreiben, KEIN Logging!
            self.text_widget.append(formatted_text.rstrip())
            self.text_widget.moveCursor(QTextCursor.MoveOperation.End)
            self.text_widget.ensureCursorVisible()

    def flush(self):
        pass


class TerminalMirrorWidget(QWidget):
    """Widget für Terminal-Spiegelung mit Logging-Integration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mirroring_active = False
        self.original_stdout = None
        self.original_stderr = None
        self.stdout_redirector = None
        self.stderr_redirector = None
        self.logger = get_logger("Terminal-Mirror")
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Benutzeroberfläche einrichten."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header mit Steuerung
        header_layout = QHBoxLayout()
        
        # Titel
        title_label = QLabel("Terminal-Ausgabe")
        title_label.setStyleSheet("font-weight: bold; color: #495057;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Nur noch Löschen-Button
        self.clear_button = QPushButton("Löschen")
        self.clear_button.clicked.connect(self.clear_output)
        self.clear_button.setFixedWidth(60)
        header_layout.addWidget(self.clear_button)
        
        layout.addLayout(header_layout)
        
        # Terminal-Ausgabe
        self.text_widget = QTextEdit()
        self.text_widget.setReadOnly(True)
        self.text_widget.setMaximumHeight(200)
        self.text_widget.setFont(QFont("Consolas", 9))
        self.text_widget.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.text_widget)
        
        # Automatisch starten
        self.start_mirroring()
        
    def start_mirroring(self):
        """Startet die Terminal-Spiegelung."""
        if self.mirroring_active:
            return
            
        try:
            # Speichere originale Streams
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # Erstelle Redirectoren
            self.stdout_redirector = StreamRedirector(self.text_widget, "stdout")
            self.stderr_redirector = StreamRedirector(self.text_widget, "stderr")
            
            # Leite Streams um
            sys.stdout = self.stdout_redirector
            sys.stderr = self.stderr_redirector
            
            # Aktiviere GUI-Ausgabe für das einheitliche Logging
            UnifiedLogger.enable_gui_output(self.text_widget)
            
            self.mirroring_active = True
            
            self.logger.info("Terminal-Spiegelung gestartet")
            self.text_widget.append("=== Terminal-Spiegelung aktiviert ===")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Starten der Terminal-Spiegelung: {e}")
            
    def stop_mirroring(self):
        """Stoppt die Terminal-Spiegelung."""
        if not self.mirroring_active:
            return
            
        try:
            # Stelle originale Streams wieder her
            if self.original_stdout:
                sys.stdout = self.original_stdout
            if self.original_stderr:
                sys.stderr = self.original_stderr
            
            # Deaktiviere GUI-Ausgabe
            UnifiedLogger.disable_gui_output()
            
            self.mirroring_active = False
            
            self.logger.info("Terminal-Spiegelung gestoppt")
            self.text_widget.append("=== Terminal-Spiegelung deaktiviert ===")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Stoppen der Terminal-Spiegelung: {e}")
            
    def clear_output(self):
        """Löscht die Terminal-Ausgabe."""
        self.text_widget.clear()
        self.logger.info("Terminal-Ausgabe gelöscht")
        
    def closeEvent(self, event):
        """Beim Schließen Terminal-Spiegelung stoppen."""
        if self.mirroring_active:
            self.stop_mirroring()
        super().closeEvent(event)


def create_terminal_mirror(parent=None) -> TerminalMirrorWidget:
    """Erstellt ein Terminal-Mirror-Widget.
    
    Args:
        parent: Parent-Widget
        
    Returns:
        Terminal-Mirror-Widget
    """
    return TerminalMirrorWidget(parent) 