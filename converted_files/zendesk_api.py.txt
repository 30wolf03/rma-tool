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
        requester_id = ticket_data['ticket']['requester_id']

        # Benutzer-Daten abrufen
        url_user = f"https://ilockit.zendesk.com/api/v2/users/{requester_id}.json"
        response_user = requests.get(url_user, headers=headers)
        response_user.raise_for_status()
        user_data = response_user.json()

        return user_data['user']['email']
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

