"""Skript zum Anzeigen der ersten Zeilen der CSV-Datei."""

from pathlib import Path
import csv
import logging

from loguru import logger

# Konfiguriere das Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def main() -> None:
    csv_path = Path(__file__).parent / "RMA Geräte Retourerfassung - ILI B2C.csv"
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Zeige die Spaltennamen
            logger.info("CSV-Spalten:")
            logger.info(f"  {', '.join(reader.fieldnames)}")
            
            # Zeige die ersten 5 Zeilen
            logger.info("\nErste 5 Zeilen der CSV-Datei:")
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                logger.info(f"\nZeile {i+1}:")
                for key, value in row.items():
                    if key == 'letzter Bearbeiter':  # Hebe die Handler-Spalte hervor
                        logger.info(f"  {key}: '{value}'")
                    else:
                        logger.info(f"  {key}: {value}")
                        
    except Exception as e:
        logger.error(f"Fehler beim Lesen der CSV-Datei: {e}")
        raise

if __name__ == "__main__":
    main() 