#!/usr/bin/env python3
"""
Direkter Test der Billbee API - ohne KeePass
"""

import requests
import json

def test_billbee_direct():
    """Testet die Billbee API direkt"""
    
    print("=== Billbee API Direkt-Test ===")
    
    # Teste beide URLs
    urls = [
        "https://api.billbee.io/api/v1/orders",
        "https://app.billbee.io/api/v1/orders"
    ]
    
    for url in urls:
        print(f"\n--- Teste URL: {url} ---")
        
        # Teste ohne Authentifizierung
        try:
            response = requests.get(url, timeout=10)
            print(f"Status (ohne Auth): {response.status_code}")
            if response.status_code != 200:
                print(f"Response: {response.text[:200]}...")
        except Exception as e:
            print(f"Fehler: {e}")
        
        # Teste mit Basic Auth (ohne API Key)
        try:
            auth = ("test_user", "test_password")
            response = requests.get(url, auth=auth, timeout=10)
            print(f"Status (mit Basic Auth): {response.status_code}")
            if response.status_code != 200:
                print(f"Response: {response.text[:200]}...")
        except Exception as e:
            print(f"Fehler: {e}")
        
        # Teste mit API Key (ohne Basic Auth)
        try:
            headers = {"X-Api-Key": "test_key", "Content-Type": "application/json"}
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status (mit API Key): {response.status_code}")
            if response.status_code != 200:
                print(f"Response: {response.text[:200]}...")
        except Exception as e:
            print(f"Fehler: {e}")
    
    print("\n=== Test mit customerEmail Parameter ===")
    
    # Teste den spezifischen Request wie Bruno
    url = "https://api.billbee.io/api/v1/orders"
    params = {"customerEmail": "michaeladingeldein@web.de"}
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}...")
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    test_billbee_direct() 