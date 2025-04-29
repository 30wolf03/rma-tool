import os
import logging
from datetime import datetime

def setup_logger():
    """Erstellt und konfiguriert einen Logger für die Anwendung."""
    # Erstelle das Logs-Verzeichnis, falls es nicht existiert
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Erstelle den Logger
    logger = logging.getLogger("RMA_Tool")
    logger.setLevel(logging.DEBUG)
    
    # Erstelle das Log-Dateiformat
    log_file = os.path.join(log_dir, f"rma_tool_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log")
    
    # Erstelle den FileHandler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Erstelle den ConsoleHandler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Erstelle das Format für die Logs
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Füge die Handler zum Logger hinzu
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class LogBlock:
    """Kontext-Manager für Log-Blöcke."""
    def __init__(self, logger, message):
        self.logger = logger
        self.message = message
        
    def __enter__(self):
        self.logger.info(f"Starte: {self.message}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info(f"Beendet: {self.message}")
        else:
            self.logger.error(f"Fehler in {self.message}: {str(exc_val)}") 