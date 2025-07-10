"""Zentrale Error-Behandlung für die Anwendung."""

from typing import Optional, Callable, Any, Dict
from PyQt6.QtWidgets import QMessageBox
from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog

from shared.utils.logger import setup_logger


class ErrorHandler:
    """Zentrale Error-Behandlung."""

    def __init__(self):
        """Initialisiere den Error Handler."""
        self.logger = setup_logger("ErrorHandler")

    def handle_error(
        self,
        error: Exception,
        title: str = "Fehler",
        show_dialog: bool = True,
        callback: Optional[Callable] = None
    ) -> None:
        """Behandle einen Fehler einheitlich.
        
        Args:
            error: Der aufgetretene Fehler
            title: Titel für die Fehlermeldung
            show_dialog: Ob ein Dialog angezeigt werden soll
            callback: Optionaler Callback nach Fehlerbehandlung
        """
        error_msg = str(error)
        self.logger.error(f"{title}: {error_msg}")

        if show_dialog:
            LoggingMessageBox.critical(None, title, error_msg)

        if callback:
            callback()

    def handle_credential_error(self, service: str, error: Exception) -> None:
        """Behandle Credential-Fehler spezifisch.
        
        Args:
            service: Name des Services (z.B. "DHL API")
            error: Der aufgetretene Fehler
        """
        title = f"{service} Credential Fehler"
        message = f"Fehler beim Laden der {service} Zugangsdaten:\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_api_error(self, api_name: str, error: Exception) -> None:
        """Behandle API-Fehler spezifisch.
        
        Args:
            api_name: Name der API (z.B. "DHL API")
            error: Der aufgetretene Fehler
        """
        title = f"{api_name} Verbindungsfehler"
        message = f"Fehler bei der Verbindung zur {api_name}:\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_database_error(self, error: Exception) -> None:
        """Behandle Datenbank-Fehler spezifisch.
        
        Args:
            error: Der aufgetretene Fehler
        """
        title = "Datenbankfehler"
        message = f"Fehler bei der Datenbankoperation:\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_ui_error(self, component: str, error: Exception) -> None:
        """Behandle UI-Fehler spezifisch.
        
        Args:
            component: Name der UI-Komponente
            error: Der aufgetretene Fehler
        """
        title = f"UI-Fehler: {component}"
        message = f"Fehler in der Benutzeroberfläche ({component}):\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_validation_error(self, field: str, error: Exception) -> None:
        """Behandle Validierungsfehler spezifisch.
        
        Args:
            field: Name des Feldes
            error: Der aufgetretene Fehler
        """
        title = f"Validierungsfehler: {field}"
        message = f"Fehler bei der Validierung des Feldes '{field}':\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_file_error(self, file_path: str, error: Exception) -> None:
        """Behandle Datei-Fehler spezifisch.
        
        Args:
            file_path: Pfad zur Datei
            error: Der aufgetretene Fehler
        """
        title = f"Dateifehler: {file_path}"
        message = f"Fehler beim Zugriff auf die Datei '{file_path}':\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_network_error(self, url: str, error: Exception) -> None:
        """Behandle Netzwerk-Fehler spezifisch.
        
        Args:
            url: URL der fehlgeschlagenen Anfrage
            error: Der aufgetretene Fehler
        """
        title = f"Netzwerkfehler: {url}"
        message = f"Fehler bei der Netzwerkanfrage an '{url}':\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_permission_error(self, resource: str, error: Exception) -> None:
        """Behandle Berechtigungsfehler spezifisch.
        
        Args:
            resource: Name der Ressource
            error: Der aufgetretene Fehler
        """
        title = f"Berechtigungsfehler: {resource}"
        message = f"Keine Berechtigung für den Zugriff auf '{resource}':\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_timeout_error(self, operation: str, error: Exception) -> None:
        """Behandle Timeout-Fehler spezifisch.
        
        Args:
            operation: Name der Operation
            error: Der aufgetretene Fehler
        """
        title = f"Timeout: {operation}"
        message = f"Die Operation '{operation}' hat zu lange gedauert:\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_memory_error(self, operation: str, error: Exception) -> None:
        """Behandle Speicherfehler spezifisch.
        
        Args:
            operation: Name der Operation
            error: Der aufgetretene Fehler
        """
        title = f"Speicherfehler: {operation}"
        message = f"Nicht genügend Speicher für die Operation '{operation}':\n{str(error)}"
        
        self.handle_error(error, title, True)

    def handle_unknown_error(self, error: Exception, context: str = "") -> None:
        """Behandle unbekannte Fehler.
        
        Args:
            error: Der aufgetretene Fehler
            context: Zusätzlicher Kontext
        """
        title = "Unbekannter Fehler"
        message = f"Ein unerwarteter Fehler ist aufgetreten"
        if context:
            message += f" in: {context}"
        message += f"\n\nFehlerdetails:\n{str(error)}"
        
        self.handle_error(error, title, True)

    def log_error_with_context(
        self, 
        error: Exception, 
        context: str = "", 
        additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Logge einen Fehler mit zusätzlichem Kontext.
        
        Args:
            error: Der aufgetretene Fehler
            context: Zusätzlicher Kontext
            additional_info: Zusätzliche Informationen
        """
        error_msg = f"Fehler: {str(error)}"
        if context:
            error_msg += f" | Kontext: {context}"
        if additional_info:
            error_msg += f" | Zusatzinfo: {additional_info}"
            
        self.logger.error(error_msg) 