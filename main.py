import os
import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QMessageBox, QHBoxLayout, QLabel
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt
from utils import setup_logger

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = setup_logger()
        self.logger.info("Hauptfenster wird initialisiert")
        
        # Setze den Fenstertitel
        self.setWindowTitle("RMA Tool")
        
        # Erstelle das zentrale Widget und Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_label = QLabel("RMA Tool")
        header_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Modul-Container
        module_container = QWidget()
        module_layout = QVBoxLayout(module_container)
        module_layout.setSpacing(20)
        
        # DHL Label Tool Button
        dhl_container = QWidget()
        dhl_layout = QHBoxLayout(dhl_container)
        
        dhl_label = QLabel("DHL Label Tool")
        dhl_label.setFont(QFont("Segoe UI", 12))
        dhl_button = QPushButton("Öffnen")
        dhl_button.clicked.connect(self.open_dhl_tool)
        
        dhl_layout.addWidget(dhl_label)
        dhl_layout.addWidget(dhl_button)
        module_layout.addWidget(dhl_container)
        
        # Füge den Modul-Container zum Hauptlayout hinzu
        main_layout.addWidget(module_container)
        
        # Lade das Stylesheet
        self.load_stylesheet()
        
        # Setze die Fenstergröße
        self.resize(600, 400)
        
        self.logger.info("Hauptfenster initialisiert")

    def load_stylesheet(self):
        """Lädt das globale Stylesheet."""
        try:
            style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "global_style.qss")
            if os.path.exists(style_path):
                with open(style_path, "r", encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
                self.logger.info("Stylesheet erfolgreich geladen")
            else:
                self.logger.error(f"Stylesheet nicht gefunden: {style_path}")
        except Exception as e:
            self.logger.error(f"Fehler beim Laden des Stylesheets: {str(e)}")

    def open_dhl_tool(self):
        """Öffnet das DHL Label Tool."""
        try:
            from modules.dhl-label-tool.label_generator import DHLLabelGenerator
            self.dhl_window = DHLLabelGenerator()
            self.dhl_window.show()
            self.logger.info("DHL Label Tool geöffnet")
        except Exception as e:
            self.logger.error(f"Fehler beim Öffnen des DHL Label Tools: {str(e)}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim Öffnen des DHL Label Tools: {str(e)}")

def main():
    try:
        app = QApplication(sys.argv)
        
        # Setze das Anwendungs-Icon
        app.setWindowIcon(QIcon("icons/icon.ico"))
        
        # Erstelle und zeige das Hauptfenster
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        logger = setup_logger()
        logger.error(f"Kritischer Fehler beim Starten der Anwendung: {str(e)}")
        QMessageBox.critical(None, "Kritischer Fehler", f"Fehler beim Starten der Anwendung:\n\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 