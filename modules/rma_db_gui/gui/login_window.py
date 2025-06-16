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
    QWidget,
)

from loguru import logger


class LoginDialog(QDialog):
    """Dialog für die Benutzeranmeldung.
    
    Dieser Dialog ermöglicht die Eingabe von Initialen und Passwort
    mit zusätzlichen Sicherheitsfunktionen wie Passwort-Sichtbarkeit.
    
    Attributes:
        initials (Optional[str]): Die eingegebenen Initialen.
        password (Optional[str]): Das eingegebene Passwort.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialisiert den Login-Dialog.
        
        Args:
            parent: Parent-Widget (optional)
        """
        super().__init__(parent)
        self.initials: Optional[str] = None
        self.password: Optional[str] = None
        
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self) -> None:
        """Richtet die Benutzeroberfläche ein."""
        self.setWindowTitle("RMA Database Login")
        self.setModal(True)
        self.setMinimumWidth(300)
        
        # Hauptlayout
        layout = QFormLayout(self)
        layout.setSpacing(10)
        
        # Initialen-Eingabe
        self.initials_edit = QLineEdit()
        self.initials_edit.setPlaceholderText("Ihre Initialen")
        self.initials_edit.setFont(QFont("Segoe UI", 10))
        self.initials_edit.setMaxLength(5)  # Maximale Länge für Initialen
        layout.addRow("Initialen:", self.initials_edit)
        
        # Passwort-Eingabe mit Toggle-Button
        pw_layout = QHBoxLayout()
        pw_layout.setSpacing(5)
        
        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_edit.setPlaceholderText("KeePass Master-Passwort")
        self.pw_edit.setFont(QFont("Segoe UI", 10))
        pw_layout.addWidget(self.pw_edit)
        
        self.toggle_btn = QPushButton("👁")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setToolTip("Passwort anzeigen/ausblenden")
        self.toggle_btn.setFixedWidth(30)
        pw_layout.addWidget(self.toggle_btn)
        
        layout.addRow("Passwort:", pw_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.ok_btn = QPushButton("Anmelden")
        self.ok_btn.setDefault(True)
        btn_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Abbrechen")
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addRow(btn_layout)
        
    def _setup_connections(self) -> None:
        """Richtet die Signal-Verbindungen ein."""
        self.toggle_btn.toggled.connect(self._toggle_password_visibility)
        self.ok_btn.clicked.connect(self._validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.initials_edit.returnPressed.connect(self._validate_and_accept)
        self.pw_edit.returnPressed.connect(self._validate_and_accept)
        
    def _toggle_password_visibility(self, checked: bool) -> None:
        """Schaltet die Sichtbarkeit des Passworts um.
        
        Args:
            checked: True wenn das Passwort sichtbar sein soll
        """
        self.pw_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked 
            else QLineEdit.EchoMode.Password
        )
        
    def _validate_and_accept(self) -> None:
        """Validiert die Eingaben und akzeptiert den Dialog wenn gültig."""
        self.initials = self.initials_edit.text().strip().upper()
        self.password = self.pw_edit.text()
        
        if not self.initials:
            QMessageBox.warning(
                self,
                "Fehler",
                "Bitte geben Sie Ihre Initialen ein."
            )
            self.initials_edit.setFocus()
            return
            
        if not self.password:
            QMessageBox.warning(
                self,
                "Fehler",
                "Bitte geben Sie das KeePass Master-Passwort ein."
            )
            self.pw_edit.setFocus()
            return
            
        logger.debug(f"Login versuch für Benutzer: {self.initials}")
        super().accept()
        
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