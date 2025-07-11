"""Terminal-Spiegelung für die RMA-Tool Anwendung.

Dieses Modul leitet stdout/stderr und Logging-Ausgaben in ein GUI-Widget um,
sodass alle Ausgaben direkt in der Anwendung sichtbar sind.
"""

import sys
import logging
from io import StringIO
from typing import Optional
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor


class BlockFormatter(logging.Formatter):
    """Formatter für strukturierte Log-Ausgabe mit Einrückung."""
    
    def format(self, record):
        # Füge Präfix für bessere Lesbarkeit hinzu
        prefix = "  "
        lines = super().format(record).split('\n')
        new_lines = [prefix + line for line in lines]
        return "\n".join(new_lines)


class StreamRedirector(StringIO):
    """Leitet stdout/stderr in ein QTextEdit-Widget um."""
    
    def __init__(self, text_widget: QTextEdit, stream_name: str = "stdout"):
        super().__init__()
        self.text_widget = text_widget
        self.stream_name = stream_name
        self.buffer = ""

    def write(self, text):
        if text:
            # Füge Stream-Name als Präfix hinzu
            if self.stream_name == "stderr":
                formatted_text = f"[ERROR] {text}"
            else:
                formatted_text = f"[OUT] {text}"
            
            self.text_widget.append(formatted_text.rstrip())
            self.buffer += text

    def flush(self):
        if self.buffer:
            self.text_widget.append(self.buffer)
            self.buffer = ""


class GUIHandler(logging.Handler):
    """Handler für das Loggen in ein QTextEdit Widget."""
    
    def __init__(self, text_widget: QTextEdit):
        super().__init__()
        self.text_widget = text_widget
        self.formatter = BlockFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def emit(self, record):
        try:
            msg = self.formatter.format(record)
            self.text_widget.append(msg)
            # Scrolle automatisch zum Ende
            self.text_widget.verticalScrollBar().setValue(
                self.text_widget.verticalScrollBar().maximum()
            )
        except Exception:
            self.handleError(record)


class TerminalMirrorWidget(QWidget):
    """Widget für die Terminal-Spiegelung mit Steuerelementen."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stdout_redirector = None
        self.stderr_redirector = None
        self.gui_handler = None
        self.original_stdout = None
        self.original_stderr = None
        self._setup_ui()
        
    def _setup_ui(self):
        """Richtet die Benutzeroberfläche ein."""
        layout = QVBoxLayout(self)
        
        # Header mit Steuerelementen
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Terminal-Ausgabe:")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Steuerungsbuttons
        self.clear_button = QPushButton("Leeren")
        self.clear_button.clicked.connect(self.clear_output)
        self.clear_button.setFixedSize(100, 35)
        header_layout.addWidget(self.clear_button)
        
        self.toggle_button = QPushButton("Pause")
        self.toggle_button.clicked.connect(self.toggle_mirroring)
        self.toggle_button.setFixedSize(100, 35)
        header_layout.addWidget(self.toggle_button)
        
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
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.text_widget)
        
        # Status
        self.status_label = QLabel("Terminal-Spiegelung aktiv")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        self.mirroring_active = False
        
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
            
            # Füge GUI-Handler zum Root-Logger hinzu
            root_logger = logging.getLogger()
            self.gui_handler = GUIHandler(self.text_widget)
            self.gui_handler.setLevel(logging.INFO)
            root_logger.addHandler(self.gui_handler)
            
            self.mirroring_active = True
            self.status_label.setText("Terminal-Spiegelung aktiv")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
            self.toggle_button.setText("Pause")
            
            self.text_widget.append("=== Terminal-Spiegelung gestartet ===\n")
            
        except Exception as e:
            self.text_widget.append(f"Fehler beim Starten der Terminal-Spiegelung: {e}\n")
            
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
                
            # Entferne GUI-Handler
            if self.gui_handler:
                root_logger = logging.getLogger()
                root_logger.removeHandler(self.gui_handler)
                
            self.mirroring_active = False
            self.status_label.setText("Terminal-Spiegelung pausiert")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 10px;")
            self.toggle_button.setText("Start")
            
            self.text_widget.append("=== Terminal-Spiegelung pausiert ===\n")
            
        except Exception as e:
            self.text_widget.append(f"Fehler beim Stoppen der Terminal-Spiegelung: {e}\n")
            
    def toggle_mirroring(self):
        """Wechselt zwischen aktiv und pausiert."""
        if self.mirroring_active:
            self.stop_mirroring()
        else:
            self.start_mirroring()
            
    def clear_output(self):
        """Leert die Terminal-Ausgabe."""
        self.text_widget.clear()
        self.text_widget.append("=== Terminal-Ausgabe geleert ===\n")
        
    def closeEvent(self, event):
        """Stoppt die Spiegelung beim Schließen."""
        self.stop_mirroring()
        super().closeEvent(event)


def create_terminal_mirror(parent=None) -> TerminalMirrorWidget:
    """Erstellt ein Terminal-Mirror-Widget.
    
    Args:
        parent: Parent-Widget
        
    Returns:
        TerminalMirrorWidget-Instanz
    """
    widget = TerminalMirrorWidget(parent)
    widget.start_mirroring()
    return widget 