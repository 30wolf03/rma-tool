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
    SSH_ENTRY,
    MYSQL_ENTRY,
    PRIVATE_KEY_ENTRY,
)
from shared.credentials.keepass_handler import CentralKeePassHandler


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

    This class provides secure access to KeePass credentials using the
    central KeePass handler, with proper error handling and type safety.
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
        self._central_handler = CentralKeePassHandler()
        self._load_database()

    def _load_database(self) -> None:
        """Load the KeePass database using the central handler.

        Raises:
            KeepassError: If the database file is not found.
            KeepassCredentialsError: If the password is invalid.
            KeepassError: If the database format is invalid.
        """
        try:
            success = self._central_handler.open_database(self.password)
            if not success:
                raise KeepassError("Failed to open KeePass database")
        except Exception as e:
            if "Invalid" in str(e) or "password" in str(e).lower():
                raise KeepassCredentialsError("Invalid KeePass master password") from e
            raise KeepassError(f"Failed to load KeePass database: {e}") from e

    def _get_entry(self, title: str) -> Dict[str, str]:
        """Get a KeePass entry by title using the central handler.

        Args:
            title: The title of the KeePass entry to retrieve.

        Returns:
            Dict containing the entry's credentials.

        Raises:
            KeepassEntryError: If the entry is not found.
        """
        if not self._central_handler.is_database_open():
            raise KeepassError("KeePass database not loaded")

        # Use the central handler to get credentials
        username, password = self._central_handler.get_credentials(title, group="Datenbank")

        if not username and not password:
            raise KeepassEntryError(f"Entry '{title}' not found in KeePass database")

        return {
            "username": username or "",
            "password": password or "",
            "url": "",  # URL not available from central handler
        }

    def get_ssh_credentials(self) -> Dict[str, str]:
        """Get SSH connection credentials using the central handler.

        Returns:
            Dict containing SSH credentials (username, password, private_key, url).

        Raises:
            KeepassEntryError: If required entries are missing.
        """
        try:
            # Use the central handler's SSH method
            return self._central_handler.get_ssh_credentials()
        except Exception as e:
            logger.error("Failed to get SSH credentials: {}", str(e))
            raise KeepassEntryError(f"Failed to get SSH credentials: {e}")

    def get_mysql_credentials(self) -> Dict[str, str]:
        """Get MySQL connection credentials using the central handler.

        Returns:
            Dict containing MySQL credentials (username, password, host).

        Raises:
            KeepassEntryError: If the MySQL entry is missing.
        """
        try:
            # Use the central handler's MySQL method
            return self._central_handler.get_mysql_credentials()
        except Exception as e:
            logger.error("Failed to get MySQL credentials: {}", str(e))
            raise KeepassEntryError(f"Failed to get MySQL credentials: {e}")