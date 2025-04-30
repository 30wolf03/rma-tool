import requests
import json
import re
from typing import Optional
from utils import setup_logger, LogBlock


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

        with LogBlock(self.logger, "Billbee API Initialisierung") as log:
            log("API Headers initialisiert")
            log("API Key geladen")
            log("Basic Auth geladen")

    def get_customer_id(self, email: str) -> Optional[str]:
        """
        Ruft die Kunden-ID basierend auf der E-Mail-Adresse ab.
        Wirft eine Exception, wenn mehrere Kunden zur gleichen E-Mail gefunden werden.
        """
        try:
            with LogBlock(self.logger, "Kundensuche") as log:
                log(f"Suche Kunde anhand E-Mail: {email}")
                
                search_endpoint = f"{self.base_url}/search"
                search_payload = {
                    "type": ["customer"],
                    "term": f'email:"{email}"'
                }
                
                log.section("API Anfrage")
                log("Sende Suchanfrage:")
                log(json.dumps(search_payload, indent=2))
                
                response = requests.post(
                    search_endpoint,
                    headers=self.headers,
                    auth=self.auth,
                    json=search_payload
                )
                response.raise_for_status()
                data = response.json()
                
                log.section("API Antwort")
                log("Suchergebnis:")
                log(json.dumps(data, indent=2))

                customers = data.get("Customers", [])
                if len(customers) > 1:
                    self.logger.error("Mehrere Kunden gefunden! Bitte überprüfen Sie die Daten.")
                    raise ValueError("Mehrere Kunden gefunden! Bitte überprüfen Sie die Daten.")
                elif len(customers) == 1:
                    customer_id = customers[0]["Id"]
                    log(f"Kunden-ID gefunden: {customer_id}")
                    return customer_id
                else:
                    log("Keine Kunden-ID gefunden!")
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
        with LogBlock(self.logger, "Kundenadressen") as log:
            customer_id = self.get_customer_id(email)
            if not customer_id:
                log("Keine Adressen, da keine Kunden-ID gefunden wurde!")
                return None

            log(f"Gefundene Kunden-ID: {customer_id}")
            address_endpoint = f"{self.base_url}/customers/{customer_id}/addresses"
            log(f"Rufe Adressen ab von: {address_endpoint}")
            
            try:
                address_response = requests.get(
                    address_endpoint,
                    headers=self.headers,
                    auth=self.auth
                )
                address_response.raise_for_status()
                address_data = address_response.json()
                
                log.section("API Antwort")
                log("Gefundene Adressdaten:")
                log(json.dumps(address_data, indent=2))
                
                if address_data.get("Data") and len(address_data["Data"]) > 0:
                    addresses = sorted(address_data["Data"], key=lambda x: x["Id"], reverse=True)
                    return addresses
                log("Keine Adressen gefunden!")
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
        with LogBlock(self.logger, "Kundenbestellungen") as log:
            customer_id = self.get_customer_id(email)
            if not customer_id:
                log("Keine Bestellungen, da keine Kunden-ID gefunden wurde!")
                return None

            log(f"Suche Bestellungen für Kunden-ID: {customer_id}")
            orders_endpoint = f"{self.base_url}/customers/{customer_id}/orders"
            
            try:
                response = requests.get(
                    orders_endpoint,
                    headers=self.headers,
                    auth=self.auth
                )
                response.raise_for_status()
                orders_data = response.json()
                
                log.section("API Antwort")
                log("Gefundene Bestellungen:")
                log(json.dumps(orders_data, indent=2))
                
                if orders_data.get("Data") and len(orders_data["Data"]) > 0:
                    return orders_data["Data"]
                else:
                    log("Keine Bestellungen gefunden!")
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
            with LogBlock(self.logger, "Seriennummernsuche") as log:
                log("Suche nach Seriennummer in den Notizen")
                
                # Suche nach dem ersten Muster: *C1-02-34567 oder C1-02-34567
                pattern1 = r'[*]?C\d{1,2}-\d{2}-\d{5}'
                match1 = re.search(pattern1, notes)
                if match1:
                    log(f"Seriennummer gefunden (Muster 1): {match1.group(0)}")
                    return match1.group(0)

                # Suche nach dem zweiten Muster: DBA01-23456
                pattern2 = r'DBA\d{2}-\d{5}'
                match2 = re.search(pattern2, notes)
                if match2:
                    log(f"Seriennummer gefunden (Muster 2): {match2.group(0)}")
                    return match2.group(0)

                log("Keine Seriennummer in den Notizen gefunden")
                return None
        except Exception as e:
            self.logger.error(f"Fehler beim Extrahieren der Seriennummer: {str(e)}")
            return None

    def get_order_notes(self, order_id: str) -> Optional[str]:
        """
        Ruft die Notizen einer Bestellung ab.
        """
        try:
            with LogBlock(self.logger, "Bestellnotizen") as log:
                # Direkter Endpunkt für die Bestellung
                order_endpoint = f"{self.base_url}/orders/{order_id}"
                log(f"Rufe Bestelldaten ab von: {order_endpoint}")
                
                response = requests.get(
                    order_endpoint,
                    headers=self.headers,
                    auth=self.auth
                )
                response.raise_for_status()
                order_data = response.json()
                
                log.section("API Antwort")
                log("Vollständige Bestelldaten:")
                log(json.dumps(order_data, indent=2))
                
                # Extrahiere die Notizen aus den Bestelldaten
                if order_data.get("Data"):
                    notes = order_data["Data"].get("SellerComment", "")
                    log(f"Gefundene Notizen (SellerComment): {notes}")
                    
                    if notes:
                        log(f"Notizen gefunden: {notes}")
                        return notes
                
                log("Keine Notizen für die Bestellung gefunden")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler beim Abrufen der Bestellnotizen: {str(e)}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"API-Antwort: {e.response.text}")
            return None
