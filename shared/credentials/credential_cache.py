"""Centralized credential caching system for the RMA-Tool.

This module provides a secure, thread-safe credential cache that allows
users to log in once and access all modules without re-authentication.
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from .keepass_handler import CentralKeePassHandler


class CredentialType(Enum):
    """Types of credentials that can be cached."""
    KEEPASS_MASTER = "keepass_master"
    USER_LOGIN = "user_login"
    DATABASE = "database"
    API = "api"


@dataclass
class CachedCredential:
    """Represents a cached credential with metadata."""
    credential_type: CredentialType
    username: str
    password: str
    timestamp: float
    expires_at: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def is_expired(self) -> bool:
        """Check if the credential has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def get_age(self) -> float:
        """Get the age of the credential in seconds."""
        return time.time() - self.timestamp


class CredentialCache:
    """Thread-safe credential cache for the RMA-Tool.
    
    This class provides a centralized cache for all credentials used
    across different modules, ensuring users only need to log in once.
    """
    
    def __init__(self, session_timeout: int = 28800):  # 8 hours default
        """Initialize the credential cache.
        
        Args:
            session_timeout: Session timeout in seconds (default: 8 hours)
        """
        self.logger = logging.getLogger(__name__)
        self._cache: Dict[str, CachedCredential] = {}
        self._lock = threading.RLock()
        self._session_timeout = session_timeout
        self._keepass_handler: Optional[CentralKeePassHandler] = None
        
        self.logger.info("Credential cache initialized")
    
    def set_keepass_handler(self, handler: CentralKeePassHandler) -> None:
        """Set the KeePass handler for credential management.
        
        Args:
            handler: The CentralKeePassHandler instance
        """
        with self._lock:
            self._keepass_handler = handler
            self.logger.debug("KeePass handler set in credential cache")
    
    def get_keepass_handler(self) -> Optional[CentralKeePassHandler]:
        """Get the KeePass handler.
        
        Returns:
            The CentralKeePassHandler instance or None if not set
        """
        return self._keepass_handler
    
    def store_credential(
        self,
        credential_type: CredentialType,
        username: str,
        password: str,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a credential in the cache.
        
        Args:
            credential_type: Type of credential to store
            username: Username/identifier for the credential
            password: Password for the credential
            expires_in: Expiration time in seconds (None for session timeout)
            metadata: Additional metadata for the credential
        """
        with self._lock:
            expires_at = None
            if expires_in is not None:
                expires_at = time.time() + expires_in
            elif credential_type != CredentialType.KEEPASS_MASTER:
                expires_at = time.time() + self._session_timeout
            
            cached_cred = CachedCredential(
                credential_type=credential_type,
                username=username,
                password=password,
                timestamp=time.time(),
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            cache_key = f"{credential_type.value}:{username}"
            self._cache[cache_key] = cached_cred
            
            self.logger.info(
                f"Stored {credential_type.value} credential for user: {username}"
            )
    
    def get_credential(
        self,
        credential_type: CredentialType,
        username: str
    ) -> Optional[Tuple[str, str]]:
        """Get a credential from the cache.
        
        Args:
            credential_type: Type of credential to retrieve
            username: Username/identifier for the credential
            
        Returns:
            Tuple of (username, password) or None if not found/expired
        """
        with self._lock:
            cache_key = f"{credential_type.value}:{username}"
            cached_cred = self._cache.get(cache_key)
            
            if cached_cred is None:
                self.logger.debug(
                    f"Credential not found: {credential_type.value}:{username}"
                )
                return None
            
            if cached_cred.is_expired():
                self.logger.info(
                    f"Credential expired: {credential_type.value}:{username}"
                )
                del self._cache[cache_key]
                return None
            
            self.logger.debug(
                f"Retrieved {credential_type.value} credential for user: {username}"
            )
            return cached_cred.username, cached_cred.password
    
    def get_user_credentials(self) -> Optional[Tuple[str, str]]:
        """Get the current user's login credentials.
        
        Returns:
            Tuple of (username, password) or None if not available
        """
        # Try to get from KeePass handler first
        if self._keepass_handler:
            user_creds = self._keepass_handler.get_user_credentials()
            if user_creds:
                return user_creds
        
        # Fallback to cache
        # For user login, we typically store with a generic key
        return self.get_credential(CredentialType.USER_LOGIN, "current_user")
    
    def has_valid_session(self) -> bool:
        """Check if there's a valid user session.
        
        Returns:
            True if there's a valid session, False otherwise
        """
        user_creds = self.get_user_credentials()
        if not user_creds:
            return False
        
        # Check if KeePass database is still open
        if self._keepass_handler and not self._keepass_handler.is_database_open():
            return False
        
        return True
    
    def clear_expired_credentials(self) -> int:
        """Clear all expired credentials from the cache.
        
        Returns:
            Number of credentials removed
        """
        with self._lock:
            expired_keys = [
                key for key, cred in self._cache.items()
                if cred.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self.logger.debug(f"Removed expired credential: {key}")
            
            return len(expired_keys)
    
    def clear_all_credentials(self) -> None:
        """Clear all credentials from the cache."""
        with self._lock:
            self._cache.clear()
            self.logger.info("All credentials cleared from cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the credential cache.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_credentials = len(self._cache)
            expired_count = len([
                cred for cred in self._cache.values()
                if cred.is_expired()
            ])
            
            type_counts = {}
            for cred in self._cache.values():
                cred_type = cred.credential_type.value
                type_counts[cred_type] = type_counts.get(cred_type, 0) + 1
            
            return {
                "total_credentials": total_credentials,
                "expired_credentials": expired_count,
                "valid_credentials": total_credentials - expired_count,
                "credential_types": type_counts,
                "session_timeout": self._session_timeout,
                "has_keepass_handler": self._keepass_handler is not None,
                "keepass_database_open": (
                    self._keepass_handler.is_database_open()
                    if self._keepass_handler else False
                )
            }


# Global credential cache instance
_credential_cache: Optional[CredentialCache] = None
_cache_lock = threading.Lock()


def get_credential_cache() -> CredentialCache:
    """Get the global credential cache instance.
    
    Returns:
        The global CredentialCache instance
    """
    global _credential_cache
    
    if _credential_cache is None:
        with _cache_lock:
            if _credential_cache is None:
                _credential_cache = CredentialCache()
    
    return _credential_cache


def initialize_credential_cache(session_timeout: int = 28800) -> CredentialCache:
    """Initialize the global credential cache.
    
    Args:
        session_timeout: Session timeout in seconds (default: 8 hours)
        
    Returns:
        The initialized CredentialCache instance
    """
    global _credential_cache
    
    with _cache_lock:
        if _credential_cache is not None:
            raise RuntimeError("Credential cache already initialized")
        
        _credential_cache = CredentialCache(session_timeout)
        return _credential_cache


def clear_credential_cache() -> None:
    """Clear the global credential cache."""
    global _credential_cache
    
    with _cache_lock:
        if _credential_cache is not None:
            _credential_cache.clear_all_credentials()
            _credential_cache = None 