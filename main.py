"""Hauptanwendung für das RMA-Tool.

Diese Datei dient als zentraler Einstiegspunkt für die gesamte Anwendung.
Sie koordiniert die verschiedenen Module (RMA-DB-GUI, DHL-Label-Tool, etc.)
und stellt die Hauptfunktionalität bereit.
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path
from typing import Optional

from loguru import logger

# Importiere die Module
from modules.rma_db_gui.gui.main_window import MainWindow
from modules.rma_db_gui.config.settings import (
    LOG_LEVEL,
    LOG_FORMAT,
    get_log_file,
    setup_logging
)
from modules.rma_db_gui.database.connection import (
    DatabaseConnection,
    DatabaseConnectionError
)
from modules.rma_db_gui.utils.keepass_handler import KeepassHandler


def parse_args() -> argparse.Namespace:
    """Parst die Kommandozeilenargumente.
    
    Returns:
        argparse.Namespace: Die geparsten Argumente
    """
    parser = argparse.ArgumentParser(
        description="RMA-Tool - Verwaltung von RMA-Anfragen und DHL-Labels"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Aktiviere Debug-Modus mit detailliertem Logging"
    )
    
    parser.add_argument(
        "--module",
        choices=["rma-db", "dhl-label", "all"],
        default="all",
        help="Wähle das zu startende Modul (Standard: all)"
    )
    
    return parser.parse_args()


def setup_environment() -> None:
    """Richtet die Umgebung für die Anwendung ein."""
    # Stelle sicher, dass wir im richtigen Verzeichnis sind
    root_dir = Path(__file__).parent
    if not (root_dir / "modules").exists():
        raise RuntimeError(
            "Konnte modules-Verzeichnis nicht finden. "
            "Bitte starten Sie die Anwendung aus dem Hauptverzeichnis."
        )


def start_rma_db_gui() -> None:
    """Startet das RMA-Datenbank GUI-Modul."""
    from PyQt6.QtWidgets import QApplication
    
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # Setze Anwendungsweite Schriftart
        from PyQt6.QtGui import QFont
        font = QFont("Segoe UI", 10)
        app.setFont(font)
        
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
        
    except Exception as e:
        logger.exception("RMA-DB-GUI konnte nicht gestartet werden")
        raise


def start_dhl_label_tool() -> None:
    """Startet das DHL-Label-Tool Modul."""
    # TODO: Implementiere DHL-Label-Tool Start
    logger.info("DHL-Label-Tool wird gestartet...")
    raise NotImplementedError("DHL-Label-Tool noch nicht implementiert")


def main() -> None:
    """Hauptfunktion der Anwendung."""
    try:
        # Parse Kommandozeilenargumente
        args = parse_args()
        
        # Setup Logging
        log_level = "DEBUG" if args.debug else LOG_LEVEL
        setup_logging(log_level)
        
        # Setup Umgebung
        setup_environment()
        
        logger.info("Starte RMA-Tool...")
        
        # Starte gewähltes Modul
        if args.module in ["rma-db", "all"]:
            start_rma_db_gui()
        elif args.module in ["dhl-label", "all"]:
            start_dhl_label_tool()
            
    except Exception as e:
        logger.exception("Anwendung konnte nicht gestartet werden")
        sys.exit(1)


if __name__ == "__main__":
    main() 