from typing import Dict, Any, Tuple, Optional
import requests
from datetime import datetime
import uuid
from modules.dhl_label_tool.utils import setup_logger

class AddressValidator:
    def __init__(self, dhl_api_client):
        """
        Initialisiert den AddressValidator mit einem DHL API Client.
        
        Args:
            dhl_api_client: Eine Instanz der DHLAPI-Klasse für API-Aufrufe
        """
        self.dhl_api = dhl_api_client
        self.logger = setup_logger()

    def validate_address(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validiert eine Adresse gegen die DHL API.
        
        Args:
            payload: Das Payload-Dictionary für die DHL API
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: 
            - bool: True wenn die Validierung erfolgreich war
            - Optional[str]: Warnmeldung falls vorhanden
            - Optional[str]: Fehlermeldung falls vorhanden
        """
        try:
            url = f"{self.dhl_api.base_url}/parcel/de/shipping/v2/orders?validate=true"
            headers = {
                "Authorization": f"Bearer {self.dhl_api.get_auth_token()}",
                "Content-Type": "application/json",
                "Message-Id": str(uuid.uuid4()),
                "Message-Time": datetime.utcnow().isoformat(),
                "Accept": "application/json"
            }
            
            self.logger.info("Sende Validierungsanfrage an DHL API")
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            
            if "status" in response_data:
                error_detail = response_data.get("status", {}).get("detail", "")
                if error_detail:
                    if "1 of 1 shipment validated OK" in error_detail:
                        self.logger.info(f"Validierung erfolgreich: {error_detail}")
                        return True, None, None
                    elif "0 of 1 shipment validated OK" in error_detail:
                        warning_message = self._get_validation_warning_message(error_detail)
                        self.logger.warning(f"Validierung fehlgeschlagen: {error_detail}")
                        return True, warning_message, None
                    elif "weak validation error" in error_detail.lower():
                        warning_message = self._get_validation_warning_message(error_detail)
                        self.logger.warning(f"Schwache Validierungswarnung: {error_detail}")
                        return True, warning_message, None
                    else:
                        warning_message = self._get_validation_warning_message(error_detail)
                        self.logger.warning(f"Validierungswarnung: {error_detail}")
                        return True, warning_message, None
            
            warning_message = "Keine Validierungsantwort von der DHL API erhalten.\nMöchten Sie trotzdem fortfahren?"
            self.logger.warning(warning_message)
            return True, warning_message, None
            
        except Exception as e:
            self.logger.error(f"Fehler bei der Adressvalidierung: {str(e)}")
            return False, None, str(e)

    def _get_validation_warning_message(self, error_detail: str) -> str:
        """Generiert eine benutzerfreundliche Warnmeldung basierend auf dem Fehlerdetail."""
        if "street" in error_detail.lower():
            return "Die eingegebene Straße konnte nicht gefunden werden.\nMöchten Sie trotzdem fortfahren?"
        elif "postal" in error_detail.lower():
            return "Die Postleitzahl konnte nicht validiert werden.\nMöchten Sie trotzdem fortfahren?"
        elif "city" in error_detail.lower():
            return "Die Stadt konnte nicht validiert werden.\nMöchten Sie trotzdem fortfahren?"
        return "Die Adresse konnte nicht vollständig validiert werden.\nMöchten Sie trotzdem fortfahren?"

    def _get_validation_error_message(self, error_detail: str) -> str:
        """Generiert eine benutzerfreundliche Fehlermeldung basierend auf dem Fehlerdetail."""
        if "street" in error_detail.lower():
            return "Die eingegebene Straße konnte nicht gefunden werden"
        elif "postal" in error_detail.lower():
            return "Die Postleitzahl ist ungültig"
        elif "city" in error_detail.lower():
            return "Die Stadt konnte nicht gefunden werden"
        return "Die Adressdaten konnten nicht validiert werden" 