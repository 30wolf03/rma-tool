import requests
import json
import logging
from typing import Optional, List
from PySide6.QtWidgets import QMessageBox
from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog, get_module_logger
from shared.utils.logger import LogBlock



class BillbeeAPI:
    def __init__(self, api_key: str, api_user: str, api_password: str, parent_widget=None):
        self.logger = get_module_logger("BillbeeAPI")
        self.base_url = "https://api.billbee.io/api/v1"
        self.api_key = api_key
        self.api_user = api_user
        self.api_password = api_password
        self.headers = {
            "X-Billbee-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.auth = (self.api_user, self.api_password)
        self.parent_widget = parent_widget  # Speichere das Parent-Widget für Popups

        with LogBlock(self.logger, logging.INFO) as log:
            log("API Headers initialisiert")
            log("API Key geladen")
            log("Basic Auth geladen")
            
            # Überprüfe die Credentials
            self._validate_credentials()

    def _validate_credentials(self):
        """Überprüft die API Credentials."""
        try:
            with LogBlock(self.logger, logging.INFO) as log:
                log("Überprüfe Billbee API Credentials...")
                
                # Teste die Credentials mit einem einfachen API-Aufruf
                test_response = requests.get(
                    f"{self.base_url}/orders",
                    headers=self.headers,
                    auth=self.auth,
                    timeout=10
                )
                
                if test_response.status_code == 200:
                    log("✅ Billbee API Credentials sind gültig")
                    return True
                elif test_response.status_code == 401:
                    self.logger.error("❌ Billbee API Credentials sind ungültig (401 Unauthorized)")
                    self._show_credential_error("Billbee API Credentials sind ungültig. Bitte überprüfen Sie die Einstellungen in KeePass.")
                    return False
                elif test_response.status_code == 403:
                    self.logger.error("❌ Billbee API Credentials haben keine Berechtigung (403 Forbidden)")
                    self._show_credential_error("Billbee API Credentials haben keine Berechtigung. Bitte überprüfen Sie die API-Berechtigungen.")
                    return False
                else:
                    self.logger.warning(f"⚠️ Unerwarteter API-Status: {test_response.status_code}")
                    return True  # Trotzdem fortfahren
                    
        except Exception as e:
            self.logger.error(f"Fehler beim Überprüfen der Billbee API Credentials: {str(e)}")
            self._show_credential_error(f"Fehler beim Überprüfen der Billbee API Credentials: {str(e)}")
            return False

    def _show_credential_error(self, message: str):
        """Zeigt eine Fehlermeldung für Credential-Probleme an."""
        try:
            if self.parent_widget:
                LoggingMessageBox.critical(self.parent_widget, "Billbee API Fehler", message)
            else:
                LoggingMessageBox.critical(None, "Billbee API Fehler", message)
        except Exception as e:
            self.logger.error(f"Fehler beim Anzeigen der Credential-Fehlermeldung: {str(e)}")

    def get_customer_id(self, email: str) -> Optional[str]:
        """
        Ruft die Kunden-ID basierend auf der E-Mail-Adresse ab.
        Wirft eine Exception, wenn mehrere Kunden zur gleichen E-Mail gefunden werden.
        """
        try:
            with LogBlock(self.logger, logging.INFO) as log:
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
                    json=search_payload,
                    timeout=30
                )
                
                # Überprüfe den Response-Status
                if response.status_code == 401:
                    self.logger.error("Billbee API: 401 Unauthorized - Credentials sind ungültig")
                    self._show_credential_error("Billbee API Credentials sind ungültig. Bitte überprüfen Sie die Einstellungen in KeePass.")
                    return None
                elif response.status_code == 403:
                    self.logger.error("Billbee API: 403 Forbidden - Keine Berechtigung")
                    self._show_credential_error("Billbee API hat keine Berechtigung für diese Operation. Bitte überprüfen Sie die API-Berechtigungen.")
                    return None
                elif response.status_code != 200:
                    self.logger.error(f"Billbee API: {response.status_code} - {response.text}")
                    return None
                
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
        with LogBlock(self.logger, logging.INFO) as log:
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
                    auth=self.auth,
                    timeout=30
                )
                
                # Überprüfe den Response-Status
                if address_response.status_code == 401:
                    self.logger.error("Billbee API: 401 Unauthorized - Credentials sind ungültig")
                    return None
                elif address_response.status_code == 403:
                    self.logger.error("Billbee API: 403 Forbidden - Keine Berechtigung")
                    return None
                elif address_response.status_code != 200:
                    self.logger.error(f"Billbee API: {address_response.status_code} - {address_response.text}")
                    return None
                
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

    def get_all_customer_ids(self, email: str) -> list:
        """
        Ruft alle Kunden-IDs basierend auf der E-Mail-Adresse ab.
        Diese Methode wird nicht mehr verwendet, da wir direkt über /orders mit customerEmail suchen.
        Behalten für Kompatibilität.
        """
        self.logger.warning("get_all_customer_ids wird nicht mehr verwendet - verwende direkte Orders-Suche")
        return []

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
            import re
            # Suche nach Seriennummern-Mustern
            patterns = [
                r'\*([A-Z]{1,3}\d{1,2}-\d{2}-\d{5})\*',  # *C1-02-34567*
                r'([A-Z]{1,3}\d{1,2}-\d{2}-\d{5})',     # C1-02-34567
                r'([A-Z]{3,5}\d{2}-\d{5})',              # DBA01-23456
                r'([A-Z]{3,5}\d{6,7})',                  # DBA0123456
            ]
            
            for pattern in patterns:
                match = re.search(pattern, notes)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            self.logger.error(f"Fehler beim Extrahieren der Seriennummer: {str(e)}")
            return None

    def get_order_notes(self, order_id: str) -> Optional[str]:
        """
        Ruft die Notizen zu einer Bestellung ab.
        """
        with LogBlock(self.logger, logging.INFO) as log:
            log(f"Rufe Notizen für Bestellung {order_id} ab")
            
            notes_endpoint = f"{self.base_url}/orders/{order_id}/notes"
            
            try:
                response = requests.get(
                    notes_endpoint,
                    headers=self.headers,
                    auth=self.auth,
                    timeout=30
                )
                
                # Überprüfe den Response-Status
                if response.status_code == 401:
                    self.logger.error("Billbee API: 401 Unauthorized - Credentials sind ungültig")
                    return None
                elif response.status_code == 403:
                    self.logger.error("Billbee API: 403 Forbidden - Keine Berechtigung")
                    return None
                elif response.status_code != 200:
                    self.logger.error(f"Billbee API: {response.status_code} - {response.text}")
                    return None
                
                response.raise_for_status()
                notes_data = response.json()
                
                log.section("API Antwort")
                log("Gefundene Notizen:")
                log(json.dumps(notes_data, indent=2))
                
                if notes_data.get("Data") and len(notes_data["Data"]) > 0:
                    # Sammle alle Notizen
                    all_notes = []
                    for note in notes_data["Data"]:
                        if note.get("Text"):
                            all_notes.append(note["Text"])
                    
                    combined_notes = "\n".join(all_notes)
                    log(f"Notizen erfolgreich abgerufen: {len(all_notes)} Notizen")
                    return combined_notes
                else:
                    log("Keine Notizen gefunden!")
                    return None
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Fehler beim Abrufen der Bestellungsnotizen: {str(e)}")
                return None
