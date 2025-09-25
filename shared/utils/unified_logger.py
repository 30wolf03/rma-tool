"""Einheitliches Logging-System für das gesamte RMA-Tool Projekt.

Dieses Modul implementiert ein zentrales loguru-basiertes Logging-System,
das für alle Module des Projekts verwendet wird.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

from loguru import logger


class UnifiedLogger:
    """Einheitliches Logging-System für das gesamte Projekt."""
    
    _initialized = False
    _log_file_path: Optional[Path] = None
    _gui_handler_id: Optional[int] = None
    _gui_widget: Optional[Any] = None # Added for GUI widget storage
    
    @classmethod
    def initialize(cls, 
                   log_level: str = "INFO",
                   log_dir: str = "logs",
                   app_name: str = "RMA-Tool",
                   enable_console: bool = True,
                   enable_file: bool = True,
                   enable_gui: bool = False,
                   gui_widget = None) -> None:
        """Initialisiert das einheitliche Logging-System.
        
        Args:
            log_level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Verzeichnis für Log-Dateien
            app_name: Name der Anwendung für Log-Dateinamen
            enable_console: Console-Ausgabe aktivieren
            enable_file: Datei-Ausgabe aktivieren
            enable_gui: GUI-Ausgabe aktivieren
            gui_widget: GUI-Widget für Log-Ausgabe
        """
        if cls._initialized:
            return
            
        # Entferne Standard-Handler
        logger.remove()
        
        # Log-Format definieren
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        # Console-Handler
        if enable_console and sys.stderr is not None:
            logger.add(
                sys.stderr,
                level=log_level,
                format=log_format,
                colorize=True
            )
        
        # Datei-Handler
        if enable_file:
            log_dir_path = Path(log_dir)
            log_dir_path.mkdir(exist_ok=True)
            
            # Chronologisch benannte Log-Datei pro Programmstart
            timestamp = datetime.now().strftime("%Y%m%d_%H-%M-%S")
            log_filename = f"{app_name.lower().replace(' ', '_')}_{timestamp}.log"
            cls._log_file_path = log_dir_path / log_filename
            
            logger.add(
                str(cls._log_file_path),
                level=log_level,
                format=log_format,
                encoding="utf-8",
                rotation=None,  # Keine automatische Rotation - eine Datei pro Start
                retention="30 days"  # Behalte Logs für 30 Tage
                # KEINE Kompression mehr
            )
        
        # GUI-Handler
        if enable_gui and gui_widget:
            cls._gui_widget = gui_widget
            cls._gui_handler_id = logger.add(
                cls._gui_sink,
                level=log_level,
                format=log_format,
                colorize=False
            )
        
        cls._initialized = True
        logger.info(f"Einheitliches Logging-System initialisiert - Level: {log_level}")
    
    @classmethod
    def _gui_sink(cls, message):
        """GUI-Sink für Live-Ausgabe im GUI."""
        record = message.record
        if hasattr(cls, '_gui_widget') and cls._gui_widget:
            formatted_message = f"{record['time'].strftime('%H:%M:%S')} | {record['level'].name} | {record['message']}"
            cls._gui_widget.append(formatted_message)
    
    @classmethod
    def get_logger(cls, name: str = "") -> "logger":
        """Gibt einen Logger für das angegebene Modul zurück.
        
        Args:
            name: Name des Moduls (z.B. "DHL-Label-Tool", "RMA-Database-GUI")
            
        Returns:
            Logger-Instanz
        """
        if not cls._initialized:
            cls.initialize()
        
        if name:
            return logger.bind(name=f"RMA-Tool.{name}")
        return logger
    
    @classmethod
    def get_log_file_path(cls) -> Optional[Path]:
        """Gibt den Pfad zur aktuellen Log-Datei zurück.
        
        Returns:
            Pfad zur Log-Datei oder None
        """
        return cls._log_file_path
    
    @classmethod
    def enable_gui_output(cls, gui_widget) -> None:
        """Aktiviert GUI-Ausgabe für ein Widget."""
        if cls._gui_handler_id:
            logger.remove(cls._gui_handler_id)
        cls._gui_widget = gui_widget
        cls._gui_handler_id = logger.add(
            cls._gui_sink,
            level="INFO",
            format="{time:HH:mm:ss} | {level} | {message}",
            colorize=False
        )
    
    @classmethod
    def disable_gui_output(cls) -> None:
        """Deaktiviert GUI-Ausgabe."""
        if cls._gui_handler_id:
            logger.remove(cls._gui_handler_id)
            cls._gui_handler_id = None
    
    @classmethod
    @contextmanager
    def log_block(cls, name: str, level: str = "INFO"):
        """Kontextmanager für strukturierte Log-Blöcke.
        
        Args:
            name: Name des Log-Blocks
            level: Log-Level für den Block
        """
        logger = cls.get_logger()
        logger.log(level, f"=== {name} ===")
        try:
            # Erstelle eine Funktion, die den Logger verwendet
            def log_func(message: str, log_level: str = level):
                logger.log(log_level, message)
            yield log_func
        finally:
            logger.log(level, f"=== {name} abgeschlossen ===")


# Convenience-Funktionen für einfache Verwendung
def get_logger(name: str = "") -> "logger":
    """Gibt einen Logger für das angegebene Modul zurück."""
    return UnifiedLogger.get_logger(name)


def initialize_logging(**kwargs) -> None:
    """Initialisiert das Logging-System."""
    UnifiedLogger.initialize(**kwargs)


def get_log_file_path() -> Optional[Path]:
    """Gibt den Pfad zur aktuellen Log-Datei zurück."""
    return UnifiedLogger.get_log_file_path()


@contextmanager
def log_block(name: str, level: str = "INFO"):
    """Kontextmanager für strukturierte Log-Blöcke."""
    with UnifiedLogger.log_block(name, level) as logger:
        yield logger 