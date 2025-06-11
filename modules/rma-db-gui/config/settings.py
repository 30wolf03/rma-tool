"""Configuration settings for the RMA Database GUI.

This module contains all configuration settings for the RMA Database GUI,
including file paths, database settings, and GUI preferences.
"""

from pathlib import Path
from typing import Tuple
from datetime import datetime

# Base paths
MODULE_DIR: Path = Path(__file__).parent.parent
CREDENTIALS_FILE: Path = MODULE_DIR / "credentials.kdbx"

# Logging settings
LOG_DIR: Path = MODULE_DIR / "logs"
LOG_LEVEL: str = "DEBUG"
LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"

def get_log_file() -> Path:
    """Get the log file path with current timestamp.
    
    Returns:
        Path: Full path to the log file with timestamp.
    """
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return LOG_DIR / f"rma_gui_{timestamp}.log"

# Database settings
DB_NAME: str = "rma"
DB_HOST: str = "localhost"
DB_PORT: int = 3306
DB_CONNECT_TIMEOUT: int = 10

# KeePass entry names
SSH_ENTRY: str = "SSH"
MYSQL_ENTRY: str = "MySQL"
PRIVATE_KEY_ENTRY: str = "traccar.ppk"

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