import os
import sys
import re
import logging
import traceback
from io import StringIO
from datetime import datetime
from PyQt5.QtWidgets import QTextEdit


class BlockFormatter(logging.Formatter):
    """
    Benutzerdefinierter Formatter, der dafür sorgt, dass jede
    Logzeile (bzw. jeder Log-Record) mit einem Rahmen versehen wird.
    """
    def format(self, record):
        message = record.getMessage()
        lines = message.splitlines() if message else []
        prefix = self.formatTime(record, self.datefmt) + " - " + record.levelname + " - "
        new_lines = [prefix + line for line in lines]
        return "\n".join(new_lines)


class LogBlock:
    """
    Kontextmanager zur Aggregation mehrerer Logmeldungen in einem
    gemeinsamen Block mit klarer visueller Trennung.
    """
    def __init__(self, logger, title=None, level=logging.INFO):
        self.logger = logger
        self.level = level
        self.title = title

    def __enter__(self):
        if self.title:
            self.logger.log(self.level, "-" * 80)
            self.logger.log(self.level, f"=== {self.title} ===")
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            self.logger.error(f"Fehler in {self.title if self.title else 'Block'}: {str(exc_value)}")
        if self.title:
            self.logger.log(self.level, "-" * 80)

    def section(self, title):
        """Erstellt eine neue Sektion innerhalb des Blocks."""
        self.logger.log(self.level, f"--- {title} ---")

    def __call__(self, message):
        self.logger.log(self.level, message)


def setup_logger():
    """Richtet den Logger ein."""
    logger = logging.getLogger("DHLLabelGenerator")
    if not logger.hasHandlers():
        # Bestimme das Basisverzeichnis
        if getattr(sys, 'frozen', False):
            # Wenn die Anwendung als ausführbare Datei läuft
            base_dir = os.path.dirname(sys.executable)
        else:
            # Wenn die Anwendung im Entwicklungsmodus läuft
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # Erstelle einen Ordner für Logs, falls noch nicht vorhanden
        log_dir = os.path.join(base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Dateiname mit Zeitstempel
        log_filename = f"dhllabeltool_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log"
        log_filepath = os.path.join(log_dir, log_filename)
        
        # Handler für Datei und Konsole
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Formatter für beide Handler
        formatter = BlockFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Handler zum Logger hinzufügen
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)
        
        # Logge den Start der Anwendung
        with LogBlock(logger, "Anwendungsstart"):
            logger.info(f"Log-Datei: {log_filepath}")
    return logger


_logger_initialized = False

def get_logger():
    """Gibt den Logger zurück."""
    global _logger_initialized
    if not _logger_initialized:
        setup_logger()
        _logger_initialized = True
    return logging.getLogger("DHLLabelGenerator")


log = get_logger()


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
        'ref_input', 'ticket_nr_input', 'weight_input'
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
        self.logger = setup_logger()

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
    logger = get_logger()
    # Entferne existierende GUI-Handler
    for handler in logger.handlers[:]:
        if isinstance(handler, GUIHandler):
            logger.removeHandler(handler)
    
    # Füge neuen GUI-Handler hinzu
    gui_handler = GUIHandler(text_widget)
    gui_handler.setLevel(logging.INFO)
    logger.addHandler(gui_handler)
    return logger
