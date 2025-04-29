import requests
import json
import re
from typing import Optional
from utils import setup_logger


class BillbeeAPI:
    def __init__(self, api_key: str, api_user: str, api_password: str):
        self.logger = setup_logger()
        self.api_key = api_key
        self.api_user = api_user
        self.api_password = api_password
        self.base_url = "https://api.billbee.io/api/v1"
        self.headers = {
            "X-Billbee-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.auth = (self.api_user, self.api_password)

        self.logger.info("Billbee API Headers initialisiert")
        self.logger.info("Billbee API Key geladen")
        self.logger.info("Billbee Basic Auth geladen")

        # Test der Authentifizierung
        try:
            test_response = requests.get(
                f"{self.base_url}/ping",
                headers=self.headers,
                auth=self.auth
            )
            test_response.raise_for_status()
            self.logger.info("Authentifizierung erfolgreich!")
        except requests.exceptions.RequestException as e:
            self.logger.info(f"Authentifizierungsfehler: {str(e)}")

    def get_customer_id(self, email: str) -> Optional[str]:
        """
        Ruft die Kunden-ID basierend auf der E-Mail-Adresse ab.
        Wirft eine Exception, wenn mehrere Kunden zur gleichen E-Mail gefunden werden.
        """
        try:
            self.logger.info(f"Suche Kunde anhand E-Mail: {email}")
            search_endpoint = f"{self.base_url}/search"
            search_payload = {
                "type": ["customer"],
                "term": f'email:"{email}"'
            }
            self.logger.info(f"Sende Suchanfrage: {json.dumps(search_payload, indent=2)}")
            response = requests.post(
                search_endpoint,
                headers=self.headers,
                auth=self.auth,
                json=search_payload
            )
            response.raise_for_status()
            data = response.json()
            self.logger.info(f"Suchergebnis: {json.dumps(data, indent=2)}")

            customers = data.get("Customers", [])
            if len(customers) > 1:
                self.logger.error("Mehrere Kunden gefunden! Bitte überprüfen Sie die Daten.")
                raise ValueError("Mehrere Kunden gefunden! Bitte überprüfen Sie die Daten.")
            elif len(customers) == 1:
                customer_id = customers[0]["Id"]
                self.logger.info(f"Kunden-ID gefunden: {customer_id}")
                return customer_id
            else:
                self.logger.info("Keine Kunden-ID gefunden!")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler beim Abrufen der Kunden-ID: {str(e)}")
            return None

    def get_all_customer_addresses(self, email: str) -> Optional[list]:
        """
        Ruft die Adressen des Kunden anhand seiner E-Mail-Adresse ab.
        Zuerst wird die Kunden-ID ermittelt und
        anschließend die zugehörigen Adressen abgerufen.
        """
        customer_id = self.get_customer_id(email)
        if not customer_id:
            self.logger.info("Keine Adressen, da keine Kunden-ID gefunden wurde!")
            return None

        self.logger.info(f"Gefundene Kunden-ID: {customer_id}")
        address_endpoint = f"{self.base_url}/customers/{customer_id}/addresses"
        self.logger.info(f"Rufe Adressen ab von: {address_endpoint}")
        self.logger.info("-" * 80)
        try:
            address_response = requests.get(
                address_endpoint,
                headers=self.headers,
                auth=self.auth
            )
            address_response.raise_for_status()
            address_data = address_response.json()
            self.logger.info(f"Gefundene Adressdaten: {json.dumps(address_data, indent=2)}")
            self.logger.info("-" * 80)
            if address_data.get("Data") and len(address_data["Data"]) > 0:
                addresses = sorted(address_data["Data"], key=lambda x: x["Id"], reverse=True)
                return addresses
            self.logger.info("Keine Adressen gefunden!")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler beim Abrufen der Kundenadressen: {str(e)}")
            return None

    def get_all_customer_orders(self, email: str):
        """
        Ruft die Bestellungen des Kunden anhand seiner E-Mail-Adresse ab.
        Zuerst wird die Kunden-ID über get_customer_id ermittelt,
        danach werden die Bestellungen über den entsprechenden Endpunkt abgerufen.
        """
        customer_id = self.get_customer_id(email)
        if not customer_id:
            self.logger.info("Keine Bestellungen, da keine Kunden-ID gefunden wurde!")
            return None

        self.logger.info(f"Suche Bestellungen für Kunden-ID: {customer_id}")
        orders_endpoint = f"{self.base_url}/customers/{customer_id}/orders"
        try:
            response = requests.get(
                orders_endpoint,
                headers=self.headers,
                auth=self.auth
            )
            response.raise_for_status()
            orders_data = response.json()
            self.logger.info(f"Gefundene Bestellungen: {json.dumps(orders_data, indent=2)}")
            self.logger.info("-" * 80)
            if orders_data.get("Data") and len(orders_data["Data"]) > 0:
                return orders_data["Data"]
            else:
                self.logger.info("Keine Bestellungen gefunden!")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler beim Abrufen der Bestellungen: {str(e)}")
            return None

    def extract_serial_number(self, notes: str) -> Optional[str]:
        """
        Extrahiert die Seriennummer aus den Notizen.
        Sucht nach Mustern wie *C1-02-34567, C1-02-34567 oder DBA01-23456.
        """
        try:
            # Suche nach dem ersten Muster: *C1-02-34567 oder C1-02-34567
            pattern1 = r'[*]?C\d{1,2}-\d{2}-\d{5}'
            match1 = re.search(pattern1, notes)
            if match1:
                return match1.group(0)

            # Suche nach dem zweiten Muster: DBA01-23456
            pattern2 = r'DBA\d{2}-\d{5}'
            match2 = re.search(pattern2, notes)
            if match2:
                return match2.group(0)

            self.logger.info("Keine Seriennummer in den Notizen gefunden")
            return None
        except Exception as e:
            self.logger.error(f"Fehler beim Extrahieren der Seriennummer: {str(e)}")
            return None

    def get_order_notes(self, order_id: str) -> Optional[str]:
        """
        Ruft die Notizen einer Bestellung ab.
        """
        try:
            # Direkter Endpunkt für die Bestellung
            order_endpoint = f"{self.base_url}/orders/{order_id}"
            self.logger.info(f"Rufe Bestelldaten ab von: {order_endpoint}")
            
            response = requests.get(
                order_endpoint,
                headers=self.headers,
                auth=self.auth
            )
            response.raise_for_status()
            order_data = response.json()
            
            # Logge die vollständige Antwort
            self.logger.info(f"Vollständige Bestelldaten: {json.dumps(order_data, indent=2)}")
            
            # Extrahiere die Notizen aus den Bestelldaten
            if order_data.get("Data"):
                notes = order_data["Data"].get("SellerComment", "")
                self.logger.info(f"Gefundene Notizen (SellerComment): {notes}")
                
                if notes:
                    self.logger.info(f"Notizen gefunden: {notes}")
                    return notes
            
            self.logger.info("Keine Notizen für die Bestellung gefunden")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler beim Abrufen der Bestellnotizen: {str(e)}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"API-Antwort: {e.response.text}")
            return None
