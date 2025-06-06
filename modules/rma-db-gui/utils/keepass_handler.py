"""Handler for KeePass credential management.

This module provides a secure way to access and manage KeePass credentials
for database and SSH connections.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from loguru import logger
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

from ..config.settings import (
    CREDENTIALS_FILE,
    SSH_ENTRY,
    MYSQL_ENTRY,
    PRIVATE_KEY_ENTRY,
)


class KeepassError(Exception):
    """Base exception for KeePass-related errors."""

    pass


class KeepassCredentialsError(KeepassError):
    """Exception raised when KeePass credentials are invalid."""

    pass


class KeepassEntryError(KeepassError):
    """Exception raised when a required KeePass entry is missing."""

    pass


class KeepassFormatError(KeepassError):
    """Exception raised when the KeePass database format is invalid."""

    pass


class KeepassHandler:
    """Handler for managing KeePass credentials.

    This class provides secure access to KeePass credentials stored in a
    KeePass database file, with proper error handling and type safety.
    """

    def __init__(self, password: str) -> None:
        """Initialize the KeepassHandler.

        Args:
            password: The master password for the KeePass database.

        Raises:
            ValueError: If password is empty.
            KeepassCredentialsError: If the password is invalid.
            KeepassError: If the KeePass database cannot be loaded.
        """
        if not password:
            raise ValueError("Password cannot be empty")

        self.password = password
        self._kp: Optional[PyKeePass] = None
        self._load_database()

    def _load_database(self) -> None:
        """Load the KeePass database.

        Raises:
            KeepassError: If the database file is not found.
            KeepassCredentialsError: If the password is invalid.
            KeepassError: If the database format is invalid.
        """
        if not CREDENTIALS_FILE.exists():
            raise KeepassError(f"Credentials file not found: {CREDENTIALS_FILE}")

        try:
            self._kp = PyKeePass(CREDENTIALS_FILE, password=self.password)
        except CredentialsError as e:
            raise KeepassCredentialsError("Invalid KeePass master password") from e
        except Exception as e:
            if "Invalid database format" in str(e):
                raise KeepassFormatError(f"Invalid KeePass database format: {e}") from e
            raise KeepassError(f"Failed to load KeePass database: {e}") from e

    def _get_entry(self, title: str) -> Dict[str, str]:
        """Get a KeePass entry by title.

        Args:
            title: The title of the KeePass entry to retrieve.

        Returns:
            Dict containing the entry's credentials.

        Raises:
            KeepassEntryError: If the entry is not found.
        """
        if not self._kp:
            raise KeepassError("KeePass database not loaded")

        entry = self._kp.find_entries(title=title, first=True)
        if not entry:
            raise KeepassEntryError(f"Entry '{title}' not found in KeePass database")

        return {
            "username": entry.username or "",
            "password": entry.password or "",
            "url": entry.url or "",
            "entry": entry,  # Speichere den kompletten Eintrag für spätere Verwendung
        }

    def get_ssh_credentials(self) -> Dict[str, str]:
        """Get SSH connection credentials.

        Returns:
            Dict containing SSH credentials (username, password, private_key, url).

        Raises:
            KeepassEntryError: If required entries are missing.
        """
        try:
            ssh_entry = self._get_entry(SSH_ENTRY)
            entry = ssh_entry["entry"]
            
            # Suche nach der angehängten OpenSSH-Key-Datei im SSH-Eintrag
            private_key = None
            for attachment in entry.attachments:
                if attachment.filename == "traccar.key":
                    private_key = attachment.data.decode('utf-8')
                    break

            if not private_key:
                raise KeepassEntryError(
                    "Private key 'traccar.key' not found in SSH entry"
                )

            return {
                "username": ssh_entry["username"],
                "password": ssh_entry["password"],
                "private_key": private_key,
                "url": ssh_entry["url"],
            }
        except KeepassEntryError as e:
            logger.error("Failed to get SSH credentials: {}", str(e))
            raise

    def get_mysql_credentials(self) -> Dict[str, str]:
        """Get MySQL connection credentials.

        Returns:
            Dict containing MySQL credentials (username, password, host).

        Raises:
            KeepassEntryError: If the MySQL entry is missing.
        """
        try:
            mysql_entry = self._get_entry(MYSQL_ENTRY)
            return {
                "username": mysql_entry["username"],
                "password": mysql_entry["password"],
                "host": mysql_entry["url"] or "localhost",
            }
        except KeepassEntryError as e:
            logger.error("Failed to get MySQL credentials: {}", str(e))
            raise 