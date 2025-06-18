import os
import requests
import json
import time
from typing import Dict, Any
from utils import setup_logger
import uuid
from datetime import datetime
import base64


class DHLAPI:
    def __init__(
        self,
        username,
        password,
        client_id,
        client_secret,
        billing_number
    ):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.billing_number = billing_number
        self.access_token = None
        self.token_expiration = 0
        self.base_url = "https://api-eu.dhl.com"
        self.logger = setup_logger()
        self.token_cache_file = "dhl_token_cache.json"
        self.load_token_cache()

    def load_token_cache(self):
        """Lädt den Token-Cache aus der Datei, falls vorhanden."""
        try:
            if os.path.exists(self.token_cache_file):
                self.logger.info(f"Token-Cache-Datei gefunden: {self.token_cache_file}")
                with open(self.token_cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.access_token = cache_data.get('access_token')
                    self.token_expiration = cache_data.get('expiration', 0)
                    
                    if self.access_token and self.token_expiration > time.time():
                        self.logger.info(f"Gültiger Token aus Cache geladen. Gültig bis: {time.ctime(self.token_expiration)}")
                        return True
                    else:
                        self.logger.info("Token im Cache ist ungültig oder abgelaufen")
                        return False
            else:
                self.logger.info("Keine Token-Cache-Datei gefunden")
                return False
        except Exception as e:
            self.logger.error(f"Fehler beim Laden des Token-Caches: {e}")
            return False

    def save_token_cache(self):
        """Speichert den aktuellen Token im Cache."""
        try:
            if not self.access_token or not self.token_expiration:
                self.logger.warning("Keine Token-Daten zum Cachen vorhanden")
                return False
                
            cache_data = {
                'access_token': self.access_token,
                'expiration': self.token_expiration
            }
            
            with open(self.token_cache_file, 'w') as f:
                json.dump(cache_data, f)
            self.logger.info(f"Token im Cache gespeichert. Gültig bis: {time.ctime(self.token_expiration)}")
            return True
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des Token-Caches: {e}")
            return False

    def log_auth_data_preview(self, auth_data):
        for key in auth_data.keys():
            self.logger.info(f"{key} geladen")

    def is_token_expired(self) -> bool:
        """Prüft, ob der Token abgelaufen ist oder bald abläuft."""
        if not self.access_token:
            self.logger.info("Kein Token vorhanden. Neuer Token benötigt.")
            return True
        if time.time() + 300 >= self.token_expiration:  # 5 Minuten Puffer
            self.logger.info("Token läuft bald ab oder ist abgelaufen.")
            return True
        return False

    def get_auth_token(self, retries=3, backoff_factor=2) -> str:
        """Holt einen neuen Auth-Token von der DHL API."""
        auth_endpoint = f"{self.base_url}/parcel/de/account/auth/ropc/v1/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        auth_data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }

        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    auth_endpoint, headers=headers, data=auth_data, timeout=10
                )
                response.raise_for_status()
                response_data = response.json()
                self.access_token = response_data.get("access_token")
                if not self.access_token:
                    raise ValueError("Kein Access-Token erhalten.")
                self.token_expiration = time.time() + 3600  # 1 Stunde Gültigkeit
                self.logger.info("Token erfolgreich generiert.")
                self.save_token_cache()  # Speichere den neuen Token im Cache
                return self.access_token

            except requests.exceptions.RequestException as e:
                wait_time = backoff_factor ** attempt
                self.logger.error(
                    f"Token-Anfrage fehlgeschlagen (Versuch {attempt}/{retries}): {e}"
                )
                if attempt < retries:
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Authentifizierung endgültig fehlgeschlagen: {e}")

    def send_label_request(self, payload, validate=False):
        """Sendet die Label-Anfrage an die DHL API."""
        url = "https://api-eu.dhl.com/parcel/de/shipping/v2/orders"
        if validate:
            url += "?validate=true"
            
        headers = {
            "Authorization": f"Bearer {self.get_auth_token()}",
            "Content-Type": "application/json",
            "Message-Id": str(uuid.uuid4()),
            "Message-Time": datetime.utcnow().isoformat(),
            "Accept": "application/json"
        }
        
        try:
            self.logger.info(f"Sende Label-Anfrage an DHL API")
            self.logger.info(f"URL: {url}")
            self.logger.info(f"Headers: {json.dumps(headers, indent=2)}")
            self.logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            
            # Bei Validierung: Prüfe auf weak validation errors
            if validate:
                self.logger.info("Validierungsantwort von DHL API:")
                self.logger.info(f"Status Code: {response.status_code}")
                self.logger.info(f"Response Headers: {dict(response.headers)}")
                self.logger.info(f"Response Body: {json.dumps(response_data, indent=2)}")
                
                if response.status_code == 400:
                    # Prüfe auf Validierungsmeldungen in den Items
                    if "items" in response_data:
                        for item in response_data["items"]:
                            if "validationMessages" in item:
                                for validation in item["validationMessages"]:
                                    validation_message = validation.get("validationMessage", "")
                                    if "street" in validation_message.lower():
                                        raise ValueError("Die eingegebene Straße konnte nicht gefunden werden")
                                    elif "postal" in validation_message.lower():
                                        raise ValueError("Die Postleitzahl ist ungültig")
                                    elif "city" in validation_message.lower():
                                        raise ValueError("Die Stadt konnte nicht gefunden werden")
                                    else:
                                        raise ValueError("Die Adressdaten konnten nicht validiert werden")
                    
                    # Fallback für andere Fehler
                    error_detail = response_data.get("status", {}).get("detail", "")
                    if "weak validation error" in error_detail:
                        self.logger.warning(f"Schwache Validierungswarnung: {error_detail}")
                        return response_data
                    else:
                        self.logger.error(f"API Fehler: {response.status_code} - {response.text}")
                        raise ValueError("Die Adressdaten konnten nicht validiert werden")
                elif response.status_code != 200:
                    self.logger.error(f"API Fehler: {response.status_code} - {response.text}")
                    raise ValueError("Die Adressvalidierung ist fehlgeschlagen")
            # Bei Label-Erstellung: Nur auf echte Fehler prüfen
            else:
                if response.status_code != 200:
                    self.logger.error(f"API Fehler: {response.status_code} - {response.text}")
                    raise ValueError("Die Label-Erstellung ist fehlgeschlagen")
                
            return response_data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Label-Anfrage fehlgeschlagen: {str(e)}")
            raise ValueError("Die Verbindung zur DHL-API ist fehlgeschlagen")

    def create_shipment_payload(self, shipper, reference, weight_value):
        """Erstellt den Payload für die DHL API."""
        # Stelle sicher, dass das Gewicht als Integer formatiert wird
        try:
            weight_value = int(float(weight_value))
        except (ValueError, TypeError):
            raise ValueError("Ungültiges Gewicht")
        
        payload = {
            "profile": "STANDARD_GRUPPENPROFIL",
            "shipments": [{
                "product": "V01PAK",
                "billingNumber": self.billing_number,
                "refNo": reference,
                "shipper": shipper,
                "consignee": {
                    "name1": "haveltec GmbH",
                    "addressStreet": "Friedrich-Franz-Straße",
                    "addressHouse": "19",
                    "name2": "Gebäude B EG",
                    "name3": reference,
                    "postalCode": "14770",
                    "city": "Brandenburg",
                    "country": "DEU",
                    "email": "support@ilockit.bike",
                    "phone": "+49 3381 7954008"
                },
                "details": {
                    "dim": {"uom": "mm", "height": 100, 
                            "length": 200, 
                            "width": 150},
                    "weight": {"uom": "g", 
                               "value": str(weight_value)}
                }
            }]
        }
        
        return payload

    def get_sender_data(
        self, name, street, house, postal_code,
        city, email, additional_info=None, phone=None
    ):
        sender_data = {
            'name1': name.strip() or 'Max Mustermann',
            'addressStreet': street.strip(),
            'addressHouse': house.strip() or '1',
            'postalCode': postal_code.strip() or '10115',
            'city': city.strip() or 'Berlin',
            'country': 'DEU',
            'email': email.strip() or 'max@example.com',
        }
        
        if additional_info:
            sender_data['name2'] = additional_info.strip()
        
        if phone:
            sender_data['phone'] = phone.strip()
        
        return sender_data

    def process_label_request(self, sender_data, reference, weight):
        """Verarbeitet die Label-Anfrage und gibt die Sendungsnummer und das Label zurück."""
        try:
            # Erstelle den Payload für die Anfrage
            shipment_payload = self.create_shipment_payload(sender_data, reference, weight)
            
            # Validiere die Adresse (nur als Warnung)
            self.logger.info("Validiere Adresse")
            validation_response = self.send_label_request(shipment_payload, validate=True)
            validation_warning = None

            # Prüfe auf Validierungsfehler und speichere sie als Warnung
            if "status" in validation_response:
                error_detail = validation_response.get("status", {}).get("detail", "")
                if error_detail:
                    # Logge die vollständige Fehlermeldung
                    self.logger.warning(f"Validierungsfehler: {error_detail}")
                    # Extrahiere nur den relevanten Teil für die UI-Anzeige
                    if "The street entered could not be found" in error_detail:
                        validation_warning = "Die eingegebene Straße konnte nicht gefunden werden."
                    else:
                        validation_warning = error_detail

            # Erstelle das Label (unabhängig von der Validierung)
            self.logger.info("Erstelle Label")
            label_response = self.send_label_request(shipment_payload)
            
            if not label_response.get("items") or not label_response["items"]:
                raise ValueError("Keine Items in der API-Antwort")
                
            shipment_no = label_response["items"][0].get("shipmentNo")
            label_b64 = label_response["items"][0].get("label", {}).get("b64", "")
            
            if not shipment_no or not label_b64:
                raise ValueError("Label konnte nicht erstellt werden: Keine Sendungsnummer oder Label in der Antwort")
            
            self.logger.info(f"Label erfolgreich erstellt. Sendungsnummer: {shipment_no}")
            return shipment_no, label_b64, validation_warning

        except Exception as e:
            self.logger.error(f"Fehler bei der Label-Erstellung: {str(e)}")
            raise
