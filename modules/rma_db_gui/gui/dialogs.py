"""Dialoge für die RMA-Datenbank-GUI.

Dieses Modul enthält verschiedene Dialoge für die Benutzerinteraktion,
wie z.B. Bestätigungsdialoge für das Löschen von Einträgen.
"""

from __future__ import annotations

from typing import Optional, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QCheckBox,
    QWidget
)

from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog


class DeleteConfirmationDialog(QDialog):
    """Dialog zur Bestätigung des Löschens von RMA-Einträgen."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        rma_numbers: Optional[List[str]] = None
    ) -> None:
        """Initialisiert den Lösch-Bestätigungsdialog.
        
        Args:
            parent: Parent-Widget
            rma_numbers: Liste der zu löschenden RMA-Nummern
        """
        super().__init__(parent)
        self.rma_numbers = rma_numbers or []
        self.delete_shipping = False
        self.delete_attachments = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Richtet die Benutzeroberfläche ein."""
        self.setWindowTitle("RMA-Einträge löschen")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Warnung
        warning_label = QLabel(
            "Warnung: Diese Aktion kann nicht rückgängig gemacht werden!"
        )
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(warning_label)
        
        # Liste der zu löschenden Einträge
        if self.rma_numbers:
            entries_label = QLabel(
                f"Folgende RMA-Einträge werden gelöscht:\n" +
                "\n".join(f"- {rma}" for rma in self.rma_numbers)
            )
            layout.addWidget(entries_label)
        
        # Optionen
        self.shipping_checkbox = QCheckBox("Zugehörige Versanddaten löschen")
        self.shipping_checkbox.setChecked(True)
        layout.addWidget(self.shipping_checkbox)
        
        self.attachments_checkbox = QCheckBox("Zugehörige Anhänge löschen")
        self.attachments_checkbox.setChecked(True)
        layout.addWidget(self.attachments_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        delete_button = QPushButton("Löschen")
        delete_button.setStyleSheet("background-color: #dc3545; color: white;")
        delete_button.clicked.connect(self._confirm_delete)
        button_layout.addWidget(delete_button)
        
        layout.addLayout(button_layout)

    def _confirm_delete(self) -> None:
        """Zeigt eine letzte Bestätigung an und akzeptiert den Dialog."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Letzte Bestätigung")
        msg.setText("Sind Sie sicher, dass Sie diese Einträge löschen möchten?")
        msg.setInformativeText("Diese Aktion kann nicht rückgängig gemacht werden!")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.delete_shipping = self.shipping_checkbox.isChecked()
            self.delete_attachments = self.attachments_checkbox.isChecked()
            self.accept() 