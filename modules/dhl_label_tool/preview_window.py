import base64
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QFont
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout


class PreviewWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Label Vorschau")
        # Setze den Pfad zur Ressource; so wird sichergestellt, dass das Bild gefunden wird.
        self.blank_label_path = ":/blank_label.png"

        # Erstelle das Vorschau-Label
        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(400, 600)  # Beispielgröße

        layout = QVBoxLayout()
        layout.addWidget(self.preview_label)
        self.setLayout(layout)

        # Starte mit einer initialen Vorschau
        self.update_preview({})

    def update_preview(self, text_data):
        """Aktualisiert die Vorschau anhand der übergebenen Textdaten.
        
        :param text_data: Dictionary mit den Schlüsseln 'sender', 'reference' und 'weight'
        """
        
        # Lade das Hintergrundbild aus den eingebetteten Ressourcen
        pixmap = QPixmap(self.blank_label_path)
        if pixmap.isNull():
            # Falls das Laden fehlschlägt, erstelle ein leeres Pixmap als Fallback
            pixmap = QPixmap(400, 600)
            pixmap.fill(Qt.white)
        
        
        painter = QPainter()
        if not painter.begin(pixmap):
            print("Fehler: QPainter konnte nicht gestartet werden.")
            return

        painter.setPen(Qt.black)

        # Schriftgrößen definieren
        sender_font = QFont("Helvetica", 8)
        reference_font_large = QFont("Helvetica", 10)
        reference_font_small = QFont("Helvetica", 6)
        weight_font = QFont("Helvetica", 9)  # Schriftgröße für das Gewicht
        weight_font.setBold(True)  # Fettgedruckt

        # Absenderadresse zeichnen
        sender_address = text_data.get("sender", "")
        painter.setFont(sender_font)
        y_offset = 45  # Startposition für die Y-Achse
        for line in sender_address.split("\n"):
            painter.drawText(33, y_offset, line)
            y_offset += 11  # Abstand zwischen den Zeilen

        # Gewicht zeichnen (unterhalb der Adresse)
        weight = text_data.get("weight", "")
        if weight:
            painter.setFont(weight_font)
            painter.drawText(240, y_offset + 132, f"{weight}")  # Nur Wert ohne Einheit anzeigen

        # Referenznummer zeichnen
        reference_number = text_data.get("reference", "").lstrip("#")
        if reference_number:
            painter.setFont(reference_font_large)
            painter.drawText(40, 124, reference_number)  # Große Referenznummer beim Empfängerbereich
            painter.setFont(reference_font_small)
            painter.drawText(56, 206, reference_number)  # Kleine Referenznummer im separaten Referenzfeld

        painter.end()
        self.preview_label.setPixmap(pixmap)
