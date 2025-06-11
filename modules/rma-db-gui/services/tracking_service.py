"""Service für die DHL-Tracking-Integration.

Dieser Service verwaltet die automatische Aktualisierung von Tracking-Status
und die Synchronisation mit der RMA-Datenbank.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from loguru import logger
import requests

from ..database.connection import DatabaseConnection
from ..models import ShippingStatus, Shipping, RMARequest


class DHLTrackingError(Exception):
    """Basis-Exception für DHL-Tracking-Fehler."""
    pass


class DHLTrackingService:
    """Service für die DHL-Tracking-Integration."""

    def __init__(self, db_connection: DatabaseConnection, api_key: str) -> None:
        """Initialisiert den DHL-Tracking-Service.
        
        Args:
            db_connection: Datenbankverbindung
            api_key: DHL-Tracking-API-Key
        """
        self.db = db_connection
        self.api_key = api_key
        self.api_base_url = "https://api-eu.dhl.com/track/shipments"

    def _get_tracking_status(self, tracking_number: str) -> Dict[str, Any]:
        """Holt den aktuellen Tracking-Status von der DHL-API.
        
        Args:
            tracking_number: Die DHL-Tracking-Nummer
            
        Returns:
            Dict mit Tracking-Informationen
            
        Raises:
            DHLTrackingError: Bei API-Fehlern
        """
        try:
            headers = {
                "DHL-API-Key": self.api_key,
                "Accept": "application/json"
            }
            response = requests.get(
                f"{self.api_base_url}/{tracking_number}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise DHLTrackingError(f"DHL API Fehler: {e}") from e

    def _map_dhl_status(self, dhl_status: str) -> ShippingStatus:
        """Mappt DHL-Status auf interne ShippingStatus-Werte.
        
        Args:
            dhl_status: Status von der DHL-API
            
        Returns:
            Entsprechender ShippingStatus
        """
        status_mapping = {
            "label_created": ShippingStatus.LABEL_CREATED,
            "in_transit": ShippingStatus.IN_TRANSIT,
            "delivered": ShippingStatus.DELIVERED,
            "delivered_to_neighbor": ShippingStatus.DELIVERED_TO_NEIGHBOR
        }
        return status_mapping.get(dhl_status.lower(), ShippingStatus.UNKNOWN)

    def update_tracking_status(self, shipping: Shipping) -> None:
        """Aktualisiert den Tracking-Status einer Sendung.
        
        Args:
            shipping: Shipping-Objekt mit Tracking-Nummer
            
        Raises:
            DHLTrackingError: Bei API- oder Datenbankfehlern
        """
        if not shipping.tracking_number:
            logger.warning("Keine Tracking-Nummer für Sendung {}", shipping.id)
            return

        try:
            # DHL-API abfragen
            tracking_data = self._get_tracking_status(shipping.tracking_number)
            
            # Status extrahieren und mappen
            dhl_status = tracking_data.get("status", {}).get("status")
            new_status = self._map_dhl_status(dhl_status)
            
            # Status aktualisieren
            with self.db.get_connection() as conn:
                shipping.status = new_status
                shipping.last_tracking_update = datetime.now()
                shipping.tracking_details = str(tracking_data)
                
                # Wenn zugestellt, auch RMA-Status aktualisieren
                if new_status == ShippingStatus.DELIVERED:
                    shipping.rma_request.update_status(new_status.value)
                
                conn.commit()
                logger.info(
                    "Tracking-Status aktualisiert für {}: {}",
                    shipping.tracking_number,
                    new_status.value
                )
                
        except Exception as e:
            logger.error(
                "Fehler beim Update des Tracking-Status für {}: {}",
                shipping.tracking_number,
                e
            )
            raise DHLTrackingError(f"Tracking-Update fehlgeschlagen: {e}") from e

    def update_all_active_shipments(self) -> None:
        """Aktualisiert den Status aller aktiven Sendungen.
        
        Sendungen werden als aktiv betrachtet, wenn sie nicht zugestellt sind
        und eine Tracking-Nummer haben.
        """
        try:
            with self.db.get_connection() as conn:
                active_shipments = conn.query(Shipping).filter(
                    Shipping.status.notin_([
                        ShippingStatus.DELIVERED,
                        ShippingStatus.DELIVERED_TO_NEIGHBOR
                    ]),
                    Shipping.tracking_number.isnot(None)
                ).all()
                
                for shipment in active_shipments:
                    try:
                        self.update_tracking_status(shipment)
                    except DHLTrackingError as e:
                        logger.warning(
                            "Konnte Status für {} nicht aktualisieren: {}",
                            shipment.tracking_number,
                            e
                        )
                        continue
                        
        except Exception as e:
            logger.error("Fehler beim Update aller Sendungen: {}", e)
            raise DHLTrackingError("Update aller Sendungen fehlgeschlagen") from e 