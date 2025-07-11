import os
import sys
import re
import logging
import traceback
from io import StringIO
from datetime import datetime
from PySide6.QtWidgets import QTextEdit
from shared.utils.logger import setup_logger, LogBlock


class BlockFormatter(logging.Formatter):
    """Formatter für strukturierte Log-Ausgabe."""
    def format(self, record):
        # Füge Präfix für bessere Lesbarkeit hinzu
        prefix = "  "
        lines = super().format(record).split('\n')
        new_lines = [prefix + line for line in lines]
        return "\n".join(new_lines)


# Zentrale Logger-Instanz für das DHL Label Tool Modul
log = setup_logger("RMA-Tool.DHL-Label-Tool")


def is_valid_email(email):
    """Validiert die E-Mail-Adresse."""
    if not email:
        return False
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def validate_inputs(input_fields):
    """Validiert die Eingabefelder."""
    log.info("Eingaben werden validiert")
    if not is_valid_email(input_fields.get('email', '')):
        log.error("Ungültige E-Mail-Adresse")
        return False

    try:
        weight_text = input_fields.get('weight', '')
        if not weight_text:
            # Wenn kein Gewicht angegeben, setze Standardgewicht
            input_fields['weight'] = '1000'
            weight = 1000
        else:
            weight = float(weight_text)
            if weight < 1000:
                # Wenn Gewicht unter 1000g, setze Standardgewicht
                input_fields['weight'] = '1000'
                weight = 1000
    except ValueError:
        log.error("Gewicht muss eine Zahl sein")
        return False

    required_fields = ['name', 'street', 'city', 'postal_code']
    for field in required_fields:
        if not input_fields.get(field, '').strip():
            log.error(f"Feld {field} darf nicht leer sein")
            return False

    log.info("Alle Eingaben sind gültig")
    return True


def clear_all_fields(window):
    """Leert alle Eingabefelder."""
    fields_to_clear = [
        'name_input', 'street_input', 'house_input', 'additional_info_input',
        'postal_input', 'city_input', 'email_input', 'phone_input',
        'ref_input', 'ticket_nr_input', 'weight_input', 'problem_description'
    ]
    for field in fields_to_clear:
        if hasattr(window, field):
            getattr(window, field).clear()
        else:
            log.warning(f"Feld {field} nicht gefunden")

    if hasattr(window, 'type_dropdown'):
        window.type_dropdown.setCurrentIndex(0)
    else:
        log.warning("type_dropdown nicht gefunden")
        
    # Leere das Bestellungen-Dropdown
    if hasattr(window, "orders_dropdown"):
        window.orders_dropdown.clear()
        window.orders_dropdown.addItem("- Bitte auswählen -")
    else:
        log.warning("orders_dropdown nicht gefunden")

    log.info("Alle Felder wurden geleert")


def validate_reference_number(reference):
    """Validiert die Referenznummer."""
    return len(reference) >= 8


def save_label_to_file(label_data, filename):
    """Speichert das generierte Label als Datei."""
    try:
        with open(filename, 'wb') as f:
            f.write(label_data)
        return True
    except Exception as e:
        log.error(f"Fehler beim Speichern des Labels: {e}")
        return False


class StreamRedirector(StringIO):
    """Leitet stdout/stderr in ein QTextEdit-Widget um."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.logger = setup_logger("RMA-Tool.DHL-Label-Tool")

    def write(self, text):
        self.text_widget.append(text)

    def flush(self):
        pass


class GUIHandler(logging.Handler):
    """Handler für das Loggen in ein QTextEdit Widget."""
    def __init__(self, text_widget: QTextEdit):
        super().__init__()
        self.text_widget = text_widget
        self.formatter = BlockFormatter(datefmt='%Y-%m-%d %H:%M:%S')

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


def add_gui_handler(text_widget: QTextEdit):
    """Fügt einen GUI-Handler zum Logger hinzu."""
    logger = log  # Verwende die zentrale Logger-Instanz
    # Entferne existierende GUI-Handler
    for handler in logger.handlers[:]:
        if isinstance(handler, GUIHandler):
            logger.removeHandler(handler)
    
    # Füge neuen GUI-Handler hinzu
    gui_handler = GUIHandler(text_widget)
    gui_handler.setLevel(logging.INFO)
    logger.addHandler(gui_handler)
    return logger


def mask_password(password: str, visible_chars: int = 5) -> str:
    """
    Kürzt ein Passwort für das Logging, sodass nur die ersten n Zeichen sichtbar sind.
    
    Args:
        password: Das zu maskierende Passwort
        visible_chars: Anzahl der sichtbaren Zeichen am Anfang (Standard: 5)
        
    Returns:
        Das maskierte Passwort im Format "XXXXX..." oder "XXXXX" wenn das Passwort kürzer ist
    """
    if not password:
        return ""
    
    if len(password) <= visible_chars:
        return "X" * len(password)
        
    return password[:visible_chars] + "..."
