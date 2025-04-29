import requests
import base64

def get_customer_email(ticket_id, email, api_token):
    try:
        # Authentifizierung mit Basic Auth
        auth_string = f"{email}/token:{api_token}"  # /token hier hinzufügen
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Content-Type': 'application/json'
        }
        
        # Ticket-Daten abrufen
        url_ticket = f"https://ilockit.zendesk.com/api/v2/tickets/{ticket_id}.json"
        response_ticket = requests.get(url_ticket, headers=headers)
        response_ticket.raise_for_status()
        ticket_data = response_ticket.json()
        
        print(f"Ticket-Daten: {ticket_data}")  # Debug-Ausgabe
        
        if 'ticket' not in ticket_data:
            raise Exception(f"Keine Ticket-Daten in der Antwort: {ticket_data}")
            
        if 'requester_id' not in ticket_data['ticket']:
            raise Exception(f"Keine Requester-ID im Ticket: {ticket_data['ticket']}")
            
        requester_id = ticket_data['ticket']['requester_id']

        # Benutzer-Daten abrufen
        url_user = f"https://ilockit.zendesk.com/api/v2/users/{requester_id}.json"
        response_user = requests.get(url_user, headers=headers)
        response_user.raise_for_status()
        user_data = response_user.json()
        
        print(f"Benutzer-Daten: {user_data}")  # Debug-Ausgabe
        
        if 'user' not in user_data:
            raise Exception(f"Keine Benutzer-Daten in der Antwort: {user_data}")
            
        if 'email' not in user_data['user']:
            raise Exception(f"Keine E-Mail-Adresse im Benutzer: {user_data['user']}")

        return user_data['user']['email']
    except requests.exceptions.RequestException as e:
        print(f"Netzwerkfehler beim Abrufen der E-Mail-Adresse: {e}")
        if hasattr(e.response, 'text'):
            print(f"API-Antwort: {e.response.text}")
        return None
    except Exception as e:
        print(f"Fehler beim Abrufen der E-Mail-Adresse: {e}")
        return None

def update_problem_description(ticket_id, email, api_token, description):
    """Aktualisiert die Problembeschreibung im Zendesk-Ticket."""
    try:
        # Authentifizierung mit Basic Auth
        auth_string = f"{email}/token:{api_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Content-Type': 'application/json'
        }
        
        # Aktuelle Ticket-Daten abrufen
        url = f"https://ilockit.zendesk.com/api/v2/tickets/{ticket_id}.json"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        ticket_data = response.json()
        
        # Aktuelle Problembeschreibung finden
        current_description = ""
        for field in ticket_data["ticket"]["custom_fields"]:
            if field["id"] == 15258544068124:
                current_description = field.get("value", "")
                break
        
        # Neue Beschreibung anhängen
        new_description = f"{current_description}\nProblem: {description}" if current_description else f"Problem: {description}"
        
        # Ticket aktualisieren
        data = {
            "ticket": {
                "custom_fields": [
                    {
                        "id": 15258544068124,
                        "value": new_description
                    }
                ]
            }
        }
        
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Problembeschreibung: {e}")
        return False

def update_serial_number(ticket_id, email, api_token, serial_number):
    """Aktualisiert die Seriennummer im Zendesk-Ticket."""
    try:
        # Authentifizierung mit Basic Auth
        auth_string = f"{email}/token:{api_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Content-Type': 'application/json'
        }
        
        # Ticket aktualisieren
        url = f"https://ilockit.zendesk.com/api/v2/tickets/{ticket_id}.json"
        data = {
            "ticket": {
                "custom_fields": [
                    {
                        "id": 360011209119,
                        "value": serial_number
                    }
                ]
            }
        }
        
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Seriennummer erfolgreich aktualisiert: {serial_number}")
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Seriennummer: {e}")
        return False

def update_order_info(ticket_id, email, api_token, order_text):
    """Aktualisiert die Bestellinformationen im Zendesk-Ticket."""
    try:
        # Authentifizierung mit Basic Auth
        auth_string = f"{email}/token:{api_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Content-Type': 'application/json'
        }
        
        # Ticket aktualisieren
        url = f"https://ilockit.zendesk.com/api/v2/tickets/{ticket_id}.json"
        data = {
            "ticket": {
                "custom_fields": [
                    {
                        "id": 360009031520,
                        "value": order_text
                    }
                ]
            }
        }
        
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Bestellinformationen erfolgreich aktualisiert: {order_text}")
        return True
    except Exception as e:
        print(f"Fehler beim Aktualisieren der Bestellinformationen: {e}")
        return False

