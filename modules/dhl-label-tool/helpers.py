import os
import sys
import logging
import re
import traceback
from io import StringIO
from datetime import datetime

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
        print(f"Fehler beim Speichern des Labels: {e}")
        return False

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
        #border = "-" * 80
        #return f"{border}\n" + "\n".join(new_lines) + f"\n{border}"
        return "\n".join(new_lines)

class LogBlock:
    """
    Kontextmanager zur Aggregation mehrerer Logmeldungen in einem
    gemeinsamen Block.
    """
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.log(self.level, "-" * 80)

    def __call__(self, message):
        self.logger.log(self.level, message)

def setup_logger():
    """Richtet den Logger ein."""
    logger = logging.getLogger("DHLLabelGenerator")
    if not logger.hasHandlers():
        # Erstelle einen Ordner für Logs, falls noch nicht vorhanden
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # Dateiname mit Zeitstempel
        log_filename = f"dhllabeltool_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log"
        log_filepath = os.path.join(log_dir, log_filename)

        # Handler für Datei und Konsole
        file_handler = logging.FileHandler(log_filepath)
        console_handler = logging.StreamHandler(sys.stdout)

        # Formatter für beide Handler
        formatter = BlockFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Handler zum Logger hinzufügen
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)
    return logger

def validate_inputs(input_fields):
    """Validiert die Eingabefelder."""
    logger = logging.getLogger("DHLLabelGenerator")
    if not is_valid_email(input_fields.get('email', '')):
        logger.error("Ungültige E-Mail-Adresse")
        return False

    try:
        weight = float(input_fields.get('weight', '0'))
        if weight <= 0:
            logger.error("Ungültiges Gewicht")
            return False
    except ValueError:
        logger.error("Gewicht muss eine Zahl sein")
        return False

    required_fields = ['name', 'street', 'city', 'postal_code']
    for field in required_fields:
        if not input_fields.get(field, '').strip():
            logger.error(f"Feld {field} darf nicht leer sein")
            return False

    logger.info("Alle Eingaben sind gültig")
    return True

def is_valid_email(email):
    """Validiert die E-Mail-Adresse."""
    if not email:
        return False
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

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
            logging.getLogger("DHLLabelGenerator").warning(f"Feld {field} nicht gefunden")

    if hasattr(window, 'type_dropdown'):
        window.type_dropdown.setCurrentIndex(0)
    else:
        logging.getLogger("DHLLabelGenerator").warning("type_dropdown nicht gefunden")

    window.log_text.append("Alle Felder wurden geleert")
    logging.getLogger("DHLLabelGenerator").info("Alle Felder wurden geleert")
