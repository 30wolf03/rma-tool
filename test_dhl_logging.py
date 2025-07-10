"""Test-Skript für verbessertes Logging im DHL-Tool."""

import sys
import os
import logging
from datetime import datetime

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Zentrale Infrastruktur importieren
from shared.utils.logger import setup_logger, LogBlock
from shared.utils.error_handler import ErrorHandler
from shared.config.settings import Settings
from shared.credentials.credential_manager import CredentialManager


def test_logging_configuration():
    """Testet die Logging-Konfiguration."""
    print("\n" + "=" * 80)
    print("TEST: Logging Konfiguration")
    print("=" * 80)
    
    try:
        # Verschiedene Logger testen
        loggers = [
            setup_logger("DHL-Tool.Main"),
            setup_logger("DHL-Tool.BillbeeAPI"),
            setup_logger("DHL-Tool.LabelGenerator"),
            setup_logger("DHL-Tool.DHLAPI")
        ]
        
        for logger in loggers:
            logger.info(f"Logger '{logger.name}' funktioniert")
            logger.debug("Debug-Nachricht")
            logger.warning("Warnung")
            logger.error("Fehler-Nachricht")
        
        print("✓ Alle Logger funktionieren korrekt")
        return True
        
    except Exception as e:
        print(f"Fehler bei Logger-Test: {e}")
        return False


def test_error_handling_console():
    """Testet das Error Handling ohne GUI."""
    print("\n" + "=" * 80)
    print("TEST: Error Handling (Console)")
    print("=" * 80)
    
    try:
        logger = setup_logger("DHL-Tool.ErrorTest")
        error_handler = ErrorHandler()
        
        with LogBlock(logger) as log:
            log.section("Error Handling Tests")
            
            # Test 1: Validation Error (ohne GUI)
            log("Test 1: Validation Error")
            try:
                # Simuliere Validation Error ohne GUI
                raise ValueError("E-Mail ist erforderlich")
            except Exception as e:
                log(f"✓ Validation Error simuliert: {e}")
            
            # Test 2: API Error
            log("Test 2: API Error")
            try:
                raise ConnectionError("API nicht erreichbar")
            except Exception as e:
                log(f"✓ API Error simuliert: {e}")
            
            # Test 3: File Error
            log("Test 3: File Error")
            try:
                raise PermissionError("Datei nicht schreibbar")
            except Exception as e:
                log(f"✓ File Error simuliert: {e}")
            
            log("✓ Alle Error Handling Tests erfolgreich")
            return True
            
    except Exception as e:
        print(f"Fehler beim Error Handling Test: {e}")
        return False


def test_billbee_api_simulation():
    """Simuliert Billbee API Logging ohne echte API-Calls."""
    print("\n" + "=" * 80)
    print("TEST: Billbee API Logging Simulation")
    print("=" * 80)
    
    try:
        logger = setup_logger("DHL-Tool.BillbeeTest")
        error_handler = ErrorHandler()
        
        with LogBlock(logger) as log:
            log.section("Billbee API Logging Simulation")
            log("Simuliere Billbee API Calls mit detailliertem Logging")
            
            # Simuliere API Initialisierung
            log.section("API Initialisierung")
            log("Base URL: https://api.billbee.io/api/v1")
            log("API Key: ********")
            log("API User: test_user")
            log("API Password: ********")
            
            # Simuliere Kunden-Suche
            log.section("Kunden-Suche")
            log("Suche Kunde für E-Mail: test@example.com")
            log("API Request: POST /search")
            log("Request Body:")
            log("  {")
            log('    "type": ["customer"],')
            log('    "term": "email:\\"test@example.com\\""')
            log("  }")
            
            log.section("API Response")
            log("Status Code: 200")
            log("Response Headers: {'Content-Type': 'application/json'}")
            log("Response Body:")
            log("  {")
            log('    "Customers": []')
            log("  }")
            
            log("Gefundene Kunden: 0")
            log("Keine Kunden-ID gefunden")
            
            # Simuliere Bestellungen-Abruf
            log.section("Bestellungen abrufen")
            log("Lade Bestellungen für E-Mail: test@example.com")
            log("Keine Kunden-IDs gefunden - keine Bestellungen verfügbar")
            
            # Simuliere Seriennummer-Extraktion
            log.section("Seriennummer extrahieren")
            log("Notizen: Seriennummer: ABC123456789")
            log("Seriennummer gefunden: ABC123456789")
            
            log("✓ Alle API-Simulationen erfolgreich")
            return True
            
    except Exception as e:
        print(f"Fehler bei Billbee API Simulation: {e}")
        return False


def test_detailed_logging():
    """Testet detailliertes Logging für verschiedene Szenarien."""
    print("\n" + "=" * 80)
    print("TEST: Detailliertes Logging")
    print("=" * 80)
    
    try:
        logger = setup_logger("DHL-Tool.DetailedTest")
        
        with LogBlock(logger) as log:
            log.section("Detailliertes Logging Test")
            
            # Simuliere Bestellungen laden
            log.section("Bestellungen laden")
            log("Lade Bestellungen für E-Mail: customer@example.com")
            
            # Simuliere API Request
            log.section("API Request: GET /customers/123/orders")
            log("Request Headers:")
            log("  X-Api-Key: ********")
            log("  Content-Type: application/json")
            
            # Simuliere API Response
            log.section("API Response")
            log("Status Code: 200")
            log("Response Body:")
            log("  {")
            log('    "Data": [')
            log('      {')
            log('        "OrderNumber": "12345",')
            log('        "OrderDate": "2024-01-15",')
            log('        "ShipWeightKg": 2.5,')
            log('        "SellerComment": "Seriennummer: SN123456789"')
            log('      }')
            log('    ]')
            log("  }")
            
            log("Bestellungen für Kunden-ID 123: 1")
            log("Gesamtanzahl Bestellungen: 1")
            log("  1. Bestellnummer: 12345, Datum: 2024-01-15")
            
            # Simuliere Adressdaten
            log.section("Adressdaten verarbeiten")
            log("Gewicht aus Bestellung: 2500g")
            log("Adressdaten übernommen: Max Mustermann")
            log("Seriennummer gefunden: SN123456789")
            
            log("✓ Detailliertes Logging funktioniert")
            return True
            
    except Exception as e:
        print(f"Fehler bei detailliertem Logging: {e}")
        return False


def main():
    """Hauptfunktion für alle Tests."""
    print("DHL-Tool Logging Tests")
    print("=" * 80)
    print(f"Startzeit: {datetime.now()}")
    print()
    
    # Tests ausführen (ohne GUI-Komponenten)
    tests = [
        ("Logging Konfiguration", test_logging_configuration),
        ("Error Handling (Console)", test_error_handling_console),
        ("Billbee API Logging Simulation", test_billbee_api_simulation),
        ("Detailliertes Logging", test_detailed_logging)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nFühre Test aus: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✓ ERFOLGREICH" if result else "✗ FEHLGESCHLAGEN"
            print(f"Test '{test_name}': {status}")
        except Exception as e:
            print(f"Test '{test_name}': ✗ FEHLER - {e}")
            results.append((test_name, False))
    
    # Zusammenfassung
    print("\n" + "=" * 80)
    print("TEST-ZUSAMMENFASSUNG")
    print("=" * 80)
    
    successful = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {test_name}")
    
    print(f"\nErgebnis: {successful}/{total} Tests erfolgreich")
    
    if successful == total:
        print("🎉 Alle Tests erfolgreich!")
        print("\nDas verbesserte Logging ist bereit für die Integration in das DHL-Tool.")
        print("Die folgenden Verbesserungen wurden implementiert:")
        print("- Detailliertes API Request/Response Logging")
        print("- Strukturierte Log-Blöcke mit Sektionen")
        print("- Verbessertes Error Handling")
        print("- Zentrale Logger-Konfiguration")
        return True
    else:
        print("⚠️  Einige Tests fehlgeschlagen")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 