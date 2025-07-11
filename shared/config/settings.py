"""Zentrale Konfiguration für die Anwendung."""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging


class Settings:
    """Zentrale Einstellungen für die Anwendung."""

    def __init__(self, config_file: Optional[Path] = None):
        """Initialisiere die Einstellungen.
        
        Args:
            config_file: Optionaler Pfad zur Konfigurationsdatei
        """
        self.config_file = config_file or Path("config.json")
        self.logger = logging.getLogger("Settings")
        self._settings: Dict[str, Any] = self._load_default_settings()
        self._load_from_file()

    def _load_default_settings(self) -> Dict[str, Any]:
        """Lade Standard-Einstellungen.
        
        Returns:
            Dictionary mit Standard-Einstellungen
        """
        return {
            "window": {
                "width": 600,
                "height": 700,
                "min_width": 600,
                "min_height": 700,
                "center_on_startup": True
            },
            "logging": {
                "level": "INFO",
                "file_rotation": True,
                "max_file_size": 10485760,  # 10MB
                "max_files": 10,
                "console_output": True,
                "cleanup": {
                    "enabled": True,
                    "max_age_days": 30,
                    "max_files": 50,
                    "auto_cleanup": True
                }
            },
            "modules": {
                "dhl_label_tool": {
                    "enabled": True,
                    "auto_start": False,
                    "window_title": "DHL Label Tool"
                },
                "rma_db_gui": {
                    "enabled": True,
                    "auto_start": False,
                    "window_title": "RMA Database GUI"
                }
            },
            "credentials": {
                "cache_timeout": 3600,  # 1 Stunde
                "auto_refresh": True,
                "secure_storage": True
            },
            "ui": {
                "theme": "default",
                "language": "de",
                "font_size": 12,
                "show_tooltips": True
            },
            "api": {
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 1
            }
        }

    def _load_from_file(self) -> None:
        """Lade Einstellungen aus Datei."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_settings = json.load(f)
                    self._merge_settings(file_settings)
                    self.logger.info(f"Einstellungen aus {self.config_file} geladen")
            except Exception as e:
                self.logger.warning(f"Fehler beim Laden der Einstellungen: {e}")

    def _merge_settings(self, file_settings: Dict[str, Any]) -> None:
        """Führe Datei-Einstellungen mit Standard-Einstellungen zusammen.
        
        Args:
            file_settings: Einstellungen aus der Datei
        """
        for key, value in file_settings.items():
            if key in self._settings:
                if isinstance(value, dict) and isinstance(self._settings[key], dict):
                    self._settings[key].update(value)
                else:
                    self._settings[key] = value
            else:
                self._settings[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Hole einen Konfigurationswert.
        
        Args:
            key: Konfigurationsschlüssel (dot-notation unterstützt)
            default: Standardwert falls nicht gefunden
            
        Returns:
            Konfigurationswert oder Standardwert
        """
        keys = key.split(".")
        value = self._settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value

    def set(self, key: str, value: Any) -> None:
        """Setze einen Konfigurationswert.
        
        Args:
            key: Konfigurationsschlüssel (dot-notation unterstützt)
            value: Neuer Wert
        """
        keys = key.split(".")
        current = self._settings
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
            
        current[keys[-1]] = value
        self._save_settings()

    def get_window_settings(self) -> Dict[str, Any]:
        """Hole Fenster-Einstellungen.
        
        Returns:
            Dictionary mit Fenster-Einstellungen
        """
        return self.get("window", {})

    def get_logging_settings(self) -> Dict[str, Any]:
        """Hole Logging-Einstellungen.
        
        Returns:
            Dictionary mit Logging-Einstellungen
        """
        return self.get("logging", {})
    
    def get_log_cleanup_settings(self) -> Dict[str, Any]:
        """Hole Log-Bereinigungseinstellungen.
        
        Returns:
            Dictionary mit Log-Bereinigungseinstellungen
        """
        return self.get("logging.cleanup", {})
    
    def is_log_cleanup_enabled(self) -> bool:
        """Prüfe ob Log-Bereinigung aktiviert ist.
        
        Returns:
            True wenn Log-Bereinigung aktiviert ist
        """
        return self.get("logging.cleanup.enabled", True)
    
    def get_log_cleanup_max_age_days(self) -> int:
        """Hole maximale Alter der Log-Dateien in Tagen.
        
        Returns:
            Maximale Alter in Tagen
        """
        return self.get("logging.cleanup.max_age_days", 30)
    
    def get_log_cleanup_max_files(self) -> int:
        """Hole maximale Anzahl der Log-Dateien.
        
        Returns:
            Maximale Anzahl der Dateien
        """
        return self.get("logging.cleanup.max_files", 50)

    def get_module_settings(self, module_name: str) -> Dict[str, Any]:
        """Hole Einstellungen für ein spezifisches Modul.
        
        Args:
            module_name: Name des Moduls
            
        Returns:
            Dictionary mit Modul-Einstellungen
        """
        return self.get(f"modules.{module_name}", {})

    def is_module_enabled(self, module_name: str) -> bool:
        """Prüfe ob ein Modul aktiviert ist.
        
        Args:
            module_name: Name des Moduls
            
        Returns:
            True wenn Modul aktiviert ist
        """
        return self.get(f"modules.{module_name}.enabled", False)

    def get_api_timeout(self) -> int:
        """Hole API Timeout-Einstellung.
        
        Returns:
            Timeout in Sekunden
        """
        return self.get("api.timeout", 30)

    def get_retry_attempts(self) -> int:
        """Hole Anzahl der Wiederholungsversuche.
        
        Returns:
            Anzahl der Versuche
        """
        return self.get("api.retry_attempts", 3)

    def get_retry_delay(self) -> int:
        """Hole Verzögerung zwischen Wiederholungsversuchen.
        
        Returns:
            Verzögerung in Sekunden
        """
        return self.get("api.retry_delay", 1)

    def get_credential_cache_timeout(self) -> int:
        """Hole Credential Cache Timeout.
        
        Returns:
            Timeout in Sekunden
        """
        return self.get("credentials.cache_timeout", 3600)

    def get_ui_language(self) -> str:
        """Hole UI-Sprache.
        
        Returns:
            Sprachcode (z.B. "de", "en")
        """
        return self.get("ui.language", "de")

    def get_font_size(self) -> int:
        """Hole Schriftgröße.
        
        Returns:
            Schriftgröße in Punkten
        """
        return self.get("ui.font_size", 12)

    def _save_settings(self) -> None:
        """Speichere Einstellungen in Datei."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Einstellungen in {self.config_file} gespeichert")
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der Einstellungen: {e}")

    def reset_to_defaults(self) -> None:
        """Setze alle Einstellungen auf Standardwerte zurück."""
        self._settings = self._load_default_settings()
        self._save_settings()
        self.logger.info("Einstellungen auf Standardwerte zurückgesetzt")

    def export_settings(self, export_path: Path) -> None:
        """Exportiere Einstellungen in eine Datei.
        
        Args:
            export_path: Pfad für die Export-Datei
        """
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Einstellungen nach {export_path} exportiert")
        except Exception as e:
            self.logger.error(f"Fehler beim Exportieren der Einstellungen: {e}")

    def import_settings(self, import_path: Path) -> None:
        """Importiere Einstellungen aus einer Datei.
        
        Args:
            import_path: Pfad zur Import-Datei
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            self._merge_settings(imported_settings)
            self._save_settings()
            self.logger.info(f"Einstellungen aus {import_path} importiert")
        except Exception as e:
            self.logger.error(f"Fehler beim Importieren der Einstellungen: {e}")

    def get_all_settings(self) -> Dict[str, Any]:
        """Hole alle Einstellungen.
        
        Returns:
            Dictionary mit allen Einstellungen
        """
        return self._settings.copy() 