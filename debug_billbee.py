#!/usr/bin/env python3
"""
Debug-Skript für Billbee API - macht den exakten Request wie Bruno
"""

import requests
import json
from shared.credentials.credential_cache import get_credential_cache

def debug_billbee_request():
    """Macht den exakten Request wie Bruno"""
    
    print("=== Billbee API Debug ===")
    
    try:
        # Credentials laden
        credential_cache = get_credential_cache()
        kp_handler = credential_cache.get_keepass_handler()
        
        if not kp_handler or not kp_handler.is_database_open():
            print("❌ KeePass-Datenbank ist nicht geöffnet!")
            print("Versuche manuell zu öffnen...")
            
            # Manuell öffnen
            from shared.credentials import CentralKeePassHandler
            kp_handler = CentralKeePassHandler()
            
            # Hier müsstest du die Credentials eingeben
            print("Bitte öffne die KeePass-Datenbank manuell und führe dann das Skript erneut aus.")
            return
        
        # Billbee Credentials aus shared Gruppe
        api_key = kp_handler.get_credentials("BillBee API Key", group="shared")[1]
        bb_auth = kp_handler.get_credentials("BillBee Basic Auth", group="shared")
        api_user = bb_auth[0]
        api_password = bb_auth[1]
        
        print(f"API Key: {api_key[:10]}...")
        print(f"API User: {api_user}")
        print(f"API Password: {api_password[:5]}...")
        
        # Exakter Bruno-Request
        url = "https://api.billbee.io/api/v1/orders"
        params = {"customerEmail": "michaeladingeldein@web.de"}
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        auth = (api_user, api_password)
        
        print(f"\n=== Request Details ===")
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
            print(f"Erste Bestellung ID: {data.get('Data', [{}])[0].get('Id', 'N/A')}")
        else:
            print(f"❌ Fehler: {response.status_code}")
            print(f"Response Text: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_billbee_request() 