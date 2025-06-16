"""Database connection handler with SSH tunnel support using sshtunnel.

This module provides a secure way to establish database connections through
an SSH tunnel, using credentials stored in a KeePass database.
"""

from __future__ import annotations

import io
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

import paramiko
import pymysql
from loguru import logger
from pymysql.cursors import DictCursor
from pymysql.connections import Connection as MySQLConnection
from sshtunnel import SSHTunnelForwarder

from ..config.settings import DB_NAME
from ..utils.keepass_handler import KeepassHandler


class DatabaseConnectionError(Exception):
    """Base exception for database connection errors."""

    pass


class SSHConnectionError(DatabaseConnectionError):
    """Exception raised when SSH connection fails."""

    pass


class MySQLConnectionError(DatabaseConnectionError):
    """Exception raised when MySQL connection fails."""

    pass


class DatabaseConnection:
    """Handler for database connections with SSH tunnel support.

    This class manages secure database connections through an SSH tunnel,
    using credentials stored in a KeePass database. It handles the lifecycle
    of both the SSH tunnel and the database connection.

    Attributes:
        keepass_handler (KeepassHandler): Handler for KeePass credentials.
        _tunnel (Optional[SSHTunnelForwarder]): Active SSH tunnel instance.
    """

    def __init__(self, keepass_handler: KeepassHandler) -> None:
        """Initialize the database connection handler.

        Args:
            keepass_handler: Instance of KeepassHandler for credentials.

        Raises:
            ValueError: If keepass_handler is None.
        """
        if keepass_handler is None:
            raise ValueError("keepass_handler cannot be None")

        self.keepass_handler: KeepassHandler = keepass_handler
        self._tunnel: Optional[SSHTunnelForwarder] = None

    def _setup_ssh_tunnel(self) -> None:
        """Set up SSH tunnel to the database server.

        This method establishes an SSH tunnel using credentials from KeePass.
        It handles the private key securely by storing it temporarily and
        loading it using paramiko.

        Raises:
            SSHConnectionError: If SSH connection fails.
            KeyError: If required credentials are missing.
        """
        tmp_key_path: Optional[str] = None
        try:
            ssh_creds: Dict[str, str] = self.keepass_handler.get_ssh_credentials()
            url: str = ssh_creds["url"]
            
            # Parse hostname and port from URL
            match: Optional[re.Match[str]] = re.match(r"^(.*?)(?::(\d+))?$", url)
            if not match:
                raise SSHConnectionError(f"Invalid SSH URL format: {url}")
            
            hostname: str = match.group(1)
            port: int = int(match.group(2)) if match.group(2) else 22

            logger.debug(
                "Attempting SSH connection to {}:{} as user {}",
                hostname,
                port,
                ssh_creds["username"]
            )
            
            # Store private key temporarily
            with tempfile.NamedTemporaryFile(delete=False, mode="wb") as tmp_key:
                tmp_key.write(ssh_creds["private_key"].encode("utf-8"))
                tmp_key_path = tmp_key.name
            logger.debug("Private key stored temporarily")

            # Load key using paramiko
            try:
                key: paramiko.RSAKey = paramiko.RSAKey.from_private_key_file(
                    tmp_key_path,
                    password=ssh_creds["password"]
                )
                logger.debug("Private key loaded successfully")
            except paramiko.PasswordRequiredException as e:
                raise SSHConnectionError(
                    "Private key is password protected but no passphrase provided"
                ) from e
            except paramiko.SSHException as e:
                raise SSHConnectionError(f"Failed to load private key: {e}") from e

            # Establish SSH tunnel
            self._tunnel = SSHTunnelForwarder(
                (hostname, port),
                ssh_username=ssh_creds["username"],
                ssh_password=ssh_creds["password"],
                ssh_pkey=key,
                remote_bind_address=("127.0.0.1", 3306),
                local_bind_address=("127.0.0.1", 0)
            )
            
            logger.debug("Starting SSH tunnel...")
            self._tunnel.start()
            logger.debug("SSH tunnel established successfully")
            
        except Exception as e:
            logger.error("SSH tunnel error: {}", str(e))
            raise SSHConnectionError(f"Failed to establish SSH tunnel: {e}") from e
            
        finally:
            # Clean up temporary key file
            if tmp_key_path and Path(tmp_key_path).exists():
                try:
                    Path(tmp_key_path).unlink()
                    logger.debug("Temporary key file removed")
                except OSError as e:
                    logger.warning("Failed to remove temporary key file: {}", e)

    def _get_mysql_connection(self) -> MySQLConnection:
        """Create MySQL connection through SSH tunnel.

        Returns:
            MySQLConnection: MySQL connection object.

        Raises:
            MySQLConnectionError: If MySQL connection fails.
            KeyError: If required credentials are missing.
        """
        if not self._tunnel or not self._tunnel.is_active:
            raise MySQLConnectionError("SSH tunnel not established")

        try:
            mysql_creds: Dict[str, str] = self.keepass_handler.get_mysql_credentials()
            logger.debug(f"MySQL-Verbindungsversuch mit Benutzer: {mysql_creds['username']}")

            connection = pymysql.connect(
                host="127.0.0.1",
                port=self._tunnel.local_bind_port,
                user=mysql_creds["username"],
                password=mysql_creds["password"],
                database=DB_NAME,
                cursorclass=DictCursor,
                connect_timeout=10,
            )
            logger.debug("MySQL-Verbindung erfolgreich hergestellt")
            return connection
        except pymysql.MySQLError as e:
            logger.error(f"MySQL-Verbindungsfehler: {e}")
            raise MySQLConnectionError(f"Failed to connect to MySQL: {e}") from e
        except KeyError as e:
            logger.error(f"Fehlende MySQL-Anmeldedaten: {e}")
            raise MySQLConnectionError(f"Missing required MySQL credentials: {e}") from e

    @contextmanager
    def get_connection(self) -> Generator[MySQLConnection, None, None]:
        """Get database connection through SSH tunnel.

        This context manager handles the lifecycle of both the SSH tunnel
        and the database connection, ensuring proper cleanup.

        Yields:
            MySQLConnection: MySQL connection object.

        Raises:
            DatabaseConnectionError: If connection fails.
        """
        try:
            if not self._tunnel or not self._tunnel.is_active:
                self._setup_ssh_tunnel()

            connection: MySQLConnection = self._get_mysql_connection()
            try:
                yield connection
            finally:
                connection.close()
        except Exception as e:
            logger.error("Database connection failed: {}", str(e))
            raise DatabaseConnectionError(f"Database connection failed: {e}") from e
        finally:
            if self._tunnel:
                self._tunnel.stop()
                self._tunnel = None

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> list[Dict[str, Any]]:
        """Execute a database query.

        Args:
            query: SQL query to execute.
            params: Optional parameters for the query.

        Returns:
            List of dictionaries containing query results.

        Raises:
            DatabaseConnectionError: If query execution fails.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or {})
                    return cursor.fetchall()
        except Exception as e:
            logger.error("Query execution failed: {}", str(e))
            raise DatabaseConnectionError(f"Query execution failed: {e}") from e 