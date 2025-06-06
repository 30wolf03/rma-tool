"""Database connection handler with SSH tunnel support using sshtunnel."""

from __future__ import annotations

import io
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
import re

import pymysql
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
    """Handler for database connections with SSH tunnel support using sshtunnel."""

    def __init__(self, keepass_handler: KeepassHandler) -> None:
        """Initialize the database connection handler.

        Args:
            keepass_handler: Instance of KeepassHandler for credentials.

        Raises:
            ValueError: If keepass_handler is None.
        """
        if keepass_handler is None:
            raise ValueError("keepass_handler cannot be None")

        self.keepass_handler = keepass_handler
        self._tunnel: Optional[SSHTunnelForwarder] = None

    def _setup_ssh_tunnel(self) -> None:
        """Set up SSH tunnel to the database server.

        Raises:
            SSHConnectionError: If SSH connection fails.
            KeyError: If required credentials are missing.
        """
        try:
            ssh_creds = self.keepass_handler.get_ssh_credentials()
            url = ssh_creds["url"]
            match = re.match(r"^(.*?)(?::(\d+))?$", url)
            if not match:
                raise SSHConnectionError(f"Invalid SSH URL format: {url}")
            hostname = match.group(1)
            port = int(match.group(2)) if match.group(2) else 22

            self._tunnel = SSHTunnelForwarder(
                (hostname, port),
                ssh_username=ssh_creds["username"],
                ssh_password=ssh_creds["password"],
                ssh_pkey=io.StringIO(ssh_creds["private_key"]),
                ssh_private_key_password=ssh_creds["password"],
                remote_bind_address=("127.0.0.1", 3306),
                local_bind_address=("127.0.0.1", 0),  # 0 = beliebiger freier Port
            )
            self._tunnel.start()
        except Exception as e:
            raise SSHConnectionError(f"Failed to establish SSH tunnel: {e}") from e

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
            mysql_creds = self.keepass_handler.get_mysql_credentials()

            return pymysql.connect(
                host="127.0.0.1",
                port=self._tunnel.local_bind_port,
                user=mysql_creds["username"],
                password=mysql_creds["password"],
                database=DB_NAME,
                cursorclass=DictCursor,
                connect_timeout=10,
            )
        except pymysql.MySQLError as e:
            raise MySQLConnectionError(f"Failed to connect to MySQL: {e}") from e
        except KeyError as e:
            raise MySQLConnectionError(f"Missing required MySQL credentials: {e}") from e

    @contextmanager
    def get_connection(self) -> Generator[MySQLConnection, None, None]:
        """Get database connection through SSH tunnel.

        Yields:
            MySQLConnection: MySQL connection object.

        Raises:
            DatabaseConnectionError: If connection fails.
        """
        try:
            if not self._tunnel or not self._tunnel.is_active:
                self._setup_ssh_tunnel()

            connection = self._get_mysql_connection()
            try:
                yield connection
            finally:
                connection.close()
        except Exception as e:
            from loguru import logger
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
            from loguru import logger
            logger.error("Query execution failed: {}", str(e))
            raise DatabaseConnectionError(f"Query execution failed: {e}") from e 