#!/usr/bin/env python3
"""
Test der Billbee Credentials aus dem laufenden Tool
"""

import requests
import json
import sys
import os
from pathlib import Path

# Füge das Projektverzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_billbee_credentials():
    """Testet die Billbee Credentials"""
    
    print("=== Billbee Credentials Test ===")
    
    try:
        # Importiere die Credential-Funktionen
        from shared.credentials.credential_cache import get_credential_cache
        
        # Versuche Credentials zu laden
        credential_cache = get_credential_cache()
        kp_handler = credential_cache.get_keepass_handler()
        
        if not kp_handler:
            print("❌ Kein KeePass Handler gefunden")
            return
        
        if not kp_handler.is_database_open():
            print("❌ KeePass-Datenbank ist nicht geöffnet")
            print("Bitte starte zuerst das RMA-Tool und öffne die KeePass-Datenbank")
            return
        
        print("✅ KeePass-Datenbank ist geöffnet")
        
        # Lade Billbee Credentials
        try:
            api_key = kp_handler.get_credentials("BillBee API Key", group="shared")[1]
            bb_auth = kp_handler.get_credentials("BillBee Basic Auth", group="shared")
            api_user = bb_auth[0]
            api_password = bb_auth[1]
            
            print(f"✅ Credentials geladen:")
            print(f"  API Key: {api_key[:10]}...")
            print(f"  API User: {api_user}")
            print(f"  API Password: {api_password[:5]}...")
            
        except Exception as e:
            print(f"❌ Fehler beim Laden der Credentials: {e}")
            return
        
        # Teste die API
        print("\n=== Teste Billbee API ===")
        
        url = "https://api.billbee.io/api/v1/orders"
        params = {"customerEmail": "michaeladingeldein@web.de"}
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        auth = (api_user, api_password)
        
        print(f"URL: {url}")
        print(f"Params: {params}")
        print(f"Headers: {headers}")
        print(f"Auth: ({api_user}, {'*' * len(api_password)})")
        
        # Request ausführen
        print(f"\n=== Sending Request ===")
        response = requests.get(url, headers=headers, auth=auth, params=params, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            total_orders = data.get("Paging", {}).get("TotalRows", 0)
            print(f"✅ Erfolg! Gefundene Bestellungen: {total_orders}")
            if data.get("Data"):
                first_order = data["Data"][0]
                print(f"Erste Bestellung ID: {first_order.get('Id', 'N/A')}")
                print(f"Erste Bestellung Nummer: {first_order.get('OrderNumber', 'N/A')}")
        else:
            print(f"❌ Fehler: {response.status_code}")
            print(f"Response Text: {response.text[:500]}")
            
            # Zusätzliche Diagnose
            if response.status_code == 403:
                print("\n💡 403 Forbidden bedeutet:")
                print("- API Key ist ungültig oder inaktiv")
                print("- User hat keine Berechtigung für diese Operation")
                print("- IP-Whitelist ist aktiviert")
            elif response.status_code == 401:
                print("\n💡 401 Unauthorized bedeutet:")
                print("- API Key oder Basic Auth Credentials sind falsch")
                print("- User/Passwort Kombination ist ungültig")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_billbee_credentials() 