"""Centralized KeePass handler for the RMA-Tool.

This module provides a unified interface for accessing credentials
from the central KeePass database with support for module-specific
and shared credentials.
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError, HeaderChecksumError


def mask_password(password: str, visible_chars: int = 5) -> str:
    """Masks a password for logging purposes.
    
    Args:
        password: The password to mask
        visible_chars: Number of visible characters at the beginning (default: 5)
        
    Returns:
        The masked password in format "XXXXX..." or "XXXXX" if password is shorter
    """
    if not password:
        return ""
    
    if len(password) <= visible_chars:
        return "X" * len(password)
        
    return password[:visible_chars] + "..."


class CentralKeePassHandler:
    """Centralized KeePass handler for all modules.
    
    This class provides a unified interface for accessing credentials
    from the central KeePass database with support for module-specific
    and shared credentials.
    """
    
    def __init__(self, database_path: Optional[str] = None) -> None:
        """Initialize the KeePass handler.
        
        Args:
            database_path: Path to the KeePass database. If None, uses default path.
        """
        self.logger = logging.getLogger(__name__)
        self.database_path = database_path or self._get_default_database_path()
        self._kp: Optional[PyKeePass] = None
        self._user_credentials: Optional[Tuple[str, str]] = None  # (initials, master_password)
        
        self.logger.info(f"CentralKeePassHandler initialized with database: {self.database_path}")
    
    def _get_default_database_path(self) -> str:
        """Get the default path to the central KeePass database.
        
        Returns:
            Path to the central credentials.kdbx file
        """
        if getattr(sys, "frozen", False):
            # When running as executable
            base_path = Path(sys.executable).parent
            return str(base_path / "credentials.kdbx")
        else:
            # When running in development mode
            base_path = Path(__file__).parent.parent.parent
            return str(base_path / "credentials.kdbx")
    
    def open_database(self, password: str) -> bool:
        """Open the KeePass database with the master password.
        
        Args:
            password: Master password for the KeePass database
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("-" * 80)
            self.logger.info(f"Attempting to open database: {self.database_path}")
            self.logger.debug(f"File exists: {os.path.exists(self.database_path)}")
            self.logger.debug(f"File size: {os.path.getsize(self.database_path)} bytes")
            self.logger.debug(f"Using master password: {mask_password(password)}")

            self._kp = PyKeePass(self.database_path, password=password)
            self.logger.info("Database opened successfully.")
            self.logger.info("-" * 80)
            return True
            
        except Exception as e:
            self.logger.error("-" * 80)
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.error(f"Error message: {str(e)}")
            self.logger.error("-" * 80)
            return False
    
    def set_user_credentials(self, initials: str, master_password: str) -> None:
        """Set the user credentials for use across all modules.
        
        Args:
            initials: User's initials/kürzel
            master_password: KeePass master password
        """
        self._user_credentials = (initials, master_password)
        self.logger.info(f"User credentials set for: {initials}")
    
    def get_user_credentials(self) -> Optional[Tuple[str, str]]:
        """Get the stored user credentials.
        
        Returns:
            Tuple of (initials, master_password) or None if not set
        """
        return self._user_credentials
    
    def get_credentials(self, entry_title: str, module: Optional[str] = None, group: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Get credentials with priority order or from a specific group.
        
        Args:
            entry_title: Title of the credential entry
            module: Module name for module-specific credentials
            group: Name of the KeePass group/Ordner (z.B. 'shared', 'DHL Label Tool')
        
        Returns:
            Tuple of (username, password) or (None, None) if not found
        """
        if not self._kp:
            self.logger.error("Database is not open.")
            return None, None

        try:
            # Wenn explizit eine Gruppe angegeben ist, suche nur dort
            if group:
                group_obj = self._kp.find_groups(name=group, first=True)
                if group_obj:
                    for entry in group_obj.entries:
                        if entry.title == entry_title:
                            self.logger.info(f"Found entry '{entry_title}' in group '{group}'")
                            return entry.username, entry.password
                self.logger.error(f"Entry '{entry_title}' not found in group '{group}'!")
                return None, None

            # Priority 1: Module-specific folder
            if module:
                module_entry_title = f"{module}/{entry_title}"
                entry = self._kp.find_entries(title=module_entry_title, first=True)
                if entry:
                    self.logger.info(f"Found module-specific entry: '{module_entry_title}'")
                    return entry.username, entry.password
            
            # Priority 2: Database folder (for database credentials)
            db_entry_title = f"Datenbank/{entry_title}"
            entry = self._kp.find_entries(title=db_entry_title, first=True)
            if entry:
                self.logger.info(f"Found database entry: '{db_entry_title}'")
                return entry.username, entry.password
            
            # Priority 3: Shared folder (for API credentials)
            shared_entry_title = f"Shared/{entry_title}"
            entry = self._kp.find_entries(title=shared_entry_title, first=True)
            if entry:
                self.logger.info(f"Found shared entry: '{shared_entry_title}'")
                return entry.username, entry.password
            
            # Priority 4: Root level (for legacy support)
            entry = self._kp.find_entries(title=entry_title, first=True)
            if entry:
                self.logger.info(f"Found root-level entry: '{entry_title}'")
                return entry.username, entry.password
            
            self.logger.error(f"Entry '{entry_title}' not found in any location!")
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error retrieving credentials: {str(e)}")
            return None, None
    
    def get_all_credentials_for_module(self, module: str) -> Dict[str, Tuple[str, str]]:
        """Get all credentials for a specific module.
        
        Args:
            module: Module name
            
        Returns:
            Dictionary mapping entry titles to (username, password) tuples
        """
        if not self._kp:
            self.logger.error("Database is not open.")
            return {}
        
        try:
            credentials = {}
            module_group = self._kp.find_groups(name=module, first=True)
            
            if module_group:
                for entry in module_group.entries:
                    credentials[entry.title] = (entry.username, entry.password)
                    self.logger.debug(f"Found credential for {module}: {entry.title}")
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Error retrieving module credentials: {str(e)}")
            return {}
    
    def is_database_open(self) -> bool:
        """Check if the database is currently open.
        
        Returns:
            True if database is open, False otherwise
        """
        return self._kp is not None

    def get_ssh_credentials(self) -> dict:
        """Get SSH connection credentials from the KeePass database.

        Returns:
            Dict containing SSH credentials (username, password, private_key, url).
        Raises:
            Exception: If required entries are missing.
        """
        if not self._kp:
            raise Exception("KeePass database not loaded")
        entry = self._kp.find_entries(title="SSH", first=True)
        if not entry:
            raise Exception("Entry 'SSH' not found in KeePass database")
        # Suche nach der angehängten OpenSSH-Key-Datei im SSH-Eintrag
        private_key = None
        for attachment in entry.attachments:
            if attachment.filename == "traccar.key":
                private_key = attachment.data.decode('utf-8')
                break
        if not private_key:
            raise Exception("Private key 'traccar.key' not found in SSH entry")
        return {
            "username": entry.username or "",
            "password": entry.password or "",
            "private_key": private_key,
            "url": entry.url or "",
        }

    def get_mysql_credentials(self) -> dict:
        """Get MySQL connection credentials from the KeePass database.

        Returns:
            Dict containing MySQL credentials (username, password, host).
        Raises:
            Exception: If the MySQL entry is missing.
        """
        if not self._kp:
            raise Exception("KeePass database not loaded")
        entry = self._kp.find_entries(title="MySQL", first=True)
        if not entry:
            raise Exception("Entry 'MySQL' not found in KeePass database")
        return {
            "username": entry.username or "",
            "password": entry.password or "",
            "host": entry.url or "localhost",
        } 