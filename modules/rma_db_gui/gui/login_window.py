"""Login window for the RMA Database GUI.

This module provides a secure login dialog for user authentication,
with support for password visibility toggling and proper validation.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog

    QWidget,
)

from loguru import logger

# Import the credential cache
from shared.credentials.credential_cache import get_credential_cache, CredentialType
from shared.credentials.keepass_handler import CentralKeePassHandler


class LoginDialog(QDialog):
    """Dialog für die Benutzeranmeldung.
    
    Dieser Dialog verwendet das zentrale Credential-Caching-System
    und zeigt nur eine Bestätigung an, wenn die Credentials verfügbar sind.
    
    Attributes:
        initials (Optional[str]): Die Initialen aus den zentralen Credentials.
        password (Optional[str]): Das Passwort aus den zentralen Credentials.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialisiert den Login-Dialog.
        
        Args:
            parent: Parent-Widget (optional)
        """
        super().__init__(parent)
        self.credential_cache = get_credential_cache()
        self.central_kp_handler = CentralKeePassHandler()
        self.initials = None
        self.password = None
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self) -> None:
        """Richtet die Benutzeroberfläche ein."""
        self.setWindowTitle("RMA Database Login")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMinimumHeight(220)
        
        # Hauptlayout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Initialen
        initials_label = QLabel("Kürzel:")
        self.initials_input = QLineEdit()
        self.initials_input.setPlaceholderText("z.B. AB")
        
        # Passwort
        password_label = QLabel("KeePass Master-Passwort:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Master-Passwort")
        
        # Button
        self.login_btn = QPushButton("Anmelden")
        self.login_btn.setDefault(True)
        self.login_btn.setMinimumHeight(40)
        
        # Layout
        layout.addWidget(initials_label)
        layout.addWidget(self.initials_input)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_btn)
        
    def _setup_connections(self) -> None:
        """Richtet die Signal-Verbindungen ein."""
        self.login_btn.clicked.connect(self._handle_login)
        self.password_input.returnPressed.connect(self._handle_login)
        self.initials_input.returnPressed.connect(self._handle_login)
        
    def _handle_login(self) -> None:
        """Handelt die Anmeldung ein."""
        initials = self.initials_input.text().strip()
        password = self.password_input.text()
        if not initials or not password:
            LoggingMessageBox.warning(self, "Fehler", "Bitte Kürzel und Passwort eingeben.")
            return
        # Versuche KeePass zu öffnen
        if not self.central_kp_handler.open_database(password):
            LoggingMessageBox.critical(self, "Fehler", "KeePass-Datenbank konnte nicht geöffnet werden.")
            return
        # Speichere Credentials im Handler und Cache
        self.central_kp_handler.set_user_credentials(initials, password)
        self.credential_cache.set_keepass_handler(self.central_kp_handler)
        self.credential_cache.store_credential(
            credential_type=CredentialType.USER_LOGIN,
            username="current_user",
            password=password,
            metadata={"initials": initials}
        )
        self.initials = initials
        self.password = password
        self.accept()
        
    def get_credentials(self) -> Tuple[str, str]:
        """Gibt die eingegebenen Anmeldedaten zurück.
        
        Returns:
            Tuple[str, str]: (Initialen, Passwort)
            
        Raises:
            ValueError: Wenn keine gültigen Anmeldedaten vorhanden sind
        """
        if not self.initials or not self.password:
            raise ValueError("Keine gültigen Anmeldedaten vorhanden")
        return self.initials, self.password 