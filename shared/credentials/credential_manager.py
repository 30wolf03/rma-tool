"""Zentrale Credential-Verwaltung für alle Module."""

from typing import Dict, Tuple, Optional
from shared.credentials.keepass_handler import CentralKeePassHandler
from shared.utils.logger import setup_logger


class CredentialManager:
    """Zentrale Verwaltung aller Credentials."""

    def __init__(self, kp_handler: CentralKeePassHandler):
        """Initialisiere den Credential Manager.
        
        Args:
            kp_handler: KeePass Handler für Credential-Zugriff
        """
        self.kp_handler = kp_handler
        self.logger = setup_logger("CredentialManager")
        self._credentials_cache: Dict[str, Tuple[str, str]] = {}

    def get_dhl_credentials(self) -> Tuple[str, str]:
        """Lade DHL API Credentials.
        
        Returns:
            Tuple aus (username, password)
            
        Raises:
            ValueError: Wenn Credentials nicht gefunden werden
        """
        if "dhl_api" not in self._credentials_cache:
            try:
                username, password = self.kp_handler.get_credentials(
                    "DHL API Zugangsdaten"
                )
                self._credentials_cache["dhl_api"] = (username, password)
                self.logger.info("DHL API Credentials geladen")
            except Exception as e:
                self.logger.error(f"Fehler beim Laden der DHL Credentials: {e}")
                raise ValueError("DHL API Credentials nicht verfügbar")

        return self._credentials_cache["dhl_api"]

    def get_dhl_client_credentials(self) -> Tuple[str, str]:
        """Lade DHL Client Credentials.
        
        Returns:
            Tuple aus (client_id, client_secret)
            
        Raises:
            ValueError: Wenn Credentials nicht gefunden werden
        """
        if "dhl_client" not in self._credentials_cache:
            try:
                client_id, client_secret = self.kp_handler.get_credentials(
                    "DHL Client Credentials"
                )
                self._credentials_cache["dhl_client"] = (client_id, client_secret)
                self.logger.info("DHL Client Credentials geladen")
            except Exception as e:
                self.logger.error(f"Fehler beim Laden der DHL Client Credentials: {e}")
                raise ValueError("DHL Client Credentials nicht verfügbar")

        return self._credentials_cache["dhl_client"]

    def get_zendesk_credentials(self) -> Tuple[str, str]:
        """Lade Zendesk API Credentials.
        
        Returns:
            Tuple aus (email, token)
            
        Raises:
            ValueError: Wenn Credentials nicht gefunden werden
        """
        if "zendesk" not in self._credentials_cache:
            try:
                email, token = self.kp_handler.get_credentials("Zendesk API Token")
                self._credentials_cache["zendesk"] = (email, token)
                self.logger.info("Zendesk Credentials geladen")
            except Exception as e:
                self.logger.error(f"Fehler beim Laden der Zendesk Credentials: {e}")
                raise ValueError("Zendesk Credentials nicht verfügbar")

        return self._credentials_cache["zendesk"]

    def get_billbee_credentials(self) -> Tuple[str, str, str]:
        """Lade Billbee API Credentials.
        
        Returns:
            Tuple aus (api_key, username, password)
            
        Raises:
            ValueError: Wenn Credentials nicht gefunden werden
        """
        if "billbee" not in self._credentials_cache:
            try:
                api_key = self.kp_handler.get_credentials("BillBee API Key")[1]
                auth = self.kp_handler.get_credentials("BillBee Basic Auth")
                username, password = auth[0], auth[1]
                self._credentials_cache["billbee"] = (api_key, username, password)
                self.logger.info("Billbee Credentials geladen")
            except Exception as e:
                self.logger.error(f"Fehler beim Laden der Billbee Credentials: {e}")
                raise ValueError("Billbee Credentials nicht verfügbar")

        return self._credentials_cache["billbee"]

    def get_dhl_billing_number(self) -> str:
        """Lade DHL Billing Number.
        
        Returns:
            DHL Billing Number
            
        Raises:
            ValueError: Wenn Billing Number nicht gefunden wird
        """
        if "dhl_billing" not in self._credentials_cache:
            try:
                billing_number = self.kp_handler.get_credentials("DHL Billing")[0]
                self._credentials_cache["dhl_billing"] = (billing_number, "")
                self.logger.info("DHL Billing Number geladen")
            except Exception as e:
                self.logger.error(f"Fehler beim Laden der DHL Billing Number: {e}")
                raise ValueError("DHL Billing Number nicht verfügbar")

        return self._credentials_cache["dhl_billing"][0]

    def clear_cache(self) -> None:
        """Leere den Credential Cache."""
        self._credentials_cache.clear()
        self.logger.info("Credential Cache geleert")

    def get_cache_stats(self) -> Dict[str, int]:
        """Hole Statistiken über den Cache.
        
        Returns:
            Dictionary mit Cache-Statistiken
        """
        return {
            "cached_credentials": len(self._credentials_cache),
            "total_entries": len(self._credentials_cache)
        } 