"""Configuration settings for the RMA Database GUI.

This module contains all configuration settings for the RMA Database GUI,
including file paths, database settings, and GUI preferences.
"""

from pathlib import Path
from typing import Tuple
from datetime import datetime

from loguru import logger
import sys

# Base paths
MODULE_DIR: Path = Path(__file__).parent.parent
CREDENTIALS_FILE: Path = MODULE_DIR / "credentials.kdbx"

# Logging settings
LOG_DIR: Path = MODULE_DIR / "logs"
LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

def get_log_file() -> Path:
    """Get the log file path with current timestamp.
    
    Returns:
        Path: Full path to the log file with timestamp.
    """
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return LOG_DIR / f"rma_gui_{timestamp}.log"

def setup_logging(level: str = LOG_LEVEL) -> None:
    """Richtet das Logging für die Anwendung ein.
    
    Args:
        level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Entferne Standard-Handler
    logger.remove()
    
    # Log in die Konsole
    logger.add(
        sys.stderr,
        level=level,
        format=LOG_FORMAT,
        colorize=True
    )
    
    # Log in die Datei
    logger.add(
        str(get_log_file()),
        level=level,
        format=LOG_FORMAT,
        encoding="utf-8",
        rotation="1 day",  # Neue Datei pro Tag
        retention="30 days",  # Behalte Logs für 30 Tage
        compression="zip"  # Komprimiere alte Logs
    )
    
    logger.info(f"Logging initialisiert mit Level: {level}")

# Database settings
DB_NAME: str = "rma"
DB_HOST: str = "localhost"
DB_PORT: int = 3306
DB_CONNECT_TIMEOUT: int = 10

# KeePass entry names
SSH_ENTRY: str = "SSH"
MYSQL_ENTRY: str = "MySQL"
PRIVATE_KEY_ENTRY: str = "traccar.key"

# GUI settings
WINDOW_TITLE: str = "RMA Database Manager"
WINDOW_SIZE: Tuple[int, int] = (1024, 768)
WINDOW_MIN_SIZE: Tuple[int, int] = (800, 600)

# Table settings
TABLE_FONT_SIZE: int = 10
TABLE_ALTERNATING_COLORS: bool = True
TABLE_SELECTION_BEHAVIOR: str = "SelectRows"
TABLE_EDIT_TRIGGERS: str = "NoEditTriggers"

# Status bar settings
STATUS_BAR_FONT_SIZE: int = 9
STATUS_MESSAGE_TIMEOUT: int = 5000  # milliseconds 