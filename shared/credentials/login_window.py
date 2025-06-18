"""Centralized login window for the RMA-Tool.

This module provides a unified login interface that can be used across
all modules in the application.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QSize, QTimer
from PyQt6.QtGui import QIcon

from ..utils.logger import setup_logger


class CentralLoginWindow(QDialog):
    """Centralized login window for KeePass database access.
    
    This class provides a unified login interface that can be used
    across all modules in the application.
    """
    
    def __init__(self, kp_handler, parent=None):
        """Initialize the login window.
        
        Args:
            kp_handler: The KeePass handler instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = setup_logger()
        self.kp_handler = kp_handler
        self._credentials: Optional[Tuple[str, str]] = None

        self.setWindowTitle("RMA-Tool - KeePass Login")
        self.setGeometry(100, 100, 350, 180)
        self.setFixedSize(350, 180)
        self.logger.info("Initializing central login window")

        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title label
        title_label = QLabel("RMA-Tool - Zentrale Anmeldung")
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            margin-bottom: 10px;
            color: #333333;
        """)
        layout.addWidget(title_label)

        # Description label
        desc_label = QLabel(
            "Bitte das Master-Passwort für die zentrale KeePass-Datenbank eingeben:"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #333333;")
        layout.addWidget(desc_label)

        # Password input section
        password_layout = QHBoxLayout()
        password_layout.setSpacing(5)
        
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Master-Passwort eingeben...")
        self.password_input.returnPressed.connect(self._handle_login)
        password_layout.addWidget(self.password_input)

        # Toggle password visibility button
        self.show_password_btn = QPushButton(self)
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setFixedSize(30, 30)
        self.show_password_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                background: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #f0f0f0;
            }
            QPushButton:pressed {
                background: #e0e0e0;
            }
        """)
        self.show_password_btn.toggled.connect(self._toggle_password_visibility)
        self.show_password_btn.setText("👁")
        password_layout.addWidget(self.show_password_btn)

        layout.addLayout(password_layout)

        # Login button
        self.login_button = QPushButton("Anmelden", self)
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self._handle_login)
        layout.addWidget(self.login_button)

        # Center window
        self._center_window()

    def _setup_animations(self) -> None:
        """Set up animation timers and properties."""
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(16)  # ~60 FPS
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_progress = 0
        self.is_animating = False
        self.animation_duration = 300  # 300ms total duration
        self.animation_start_time = 0
        self.is_closing = True  # Animation direction

    def _center_window(self) -> None:
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        screen_center = screen.availableGeometry().center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

    def _update_animation(self) -> None:
        """Update the icon animation."""
        current_time = time.time() * 1000  # Convert to milliseconds
        elapsed = current_time - self.animation_start_time
        
        if elapsed >= self.animation_duration:
            self.animation_timer.stop()
            self.is_animating = False
            # Set final icon
            self.show_password_btn.setText("👁" if self.show_password_btn.isChecked() else "👁")
            return

        # Calculate current animation progress (0.0 to 1.0)
        progress = elapsed / self.animation_duration
        
        # Simple animation - could be enhanced with SVG
        if self.is_closing:
            progress = 1.0 - progress
        
        # Update icon based on progress
        if progress > 0.5:
            self.show_password_btn.setText("👁")
        else:
            self.show_password_btn.setText("👁")

    def _toggle_password_visibility(self, checked: bool) -> None:
        """Toggle password visibility."""
        if checked:
            self.logger.info("Password visibility activated")
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.is_closing = False  # Opening animation
        else:
            self.logger.info("Password visibility deactivated")
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.is_closing = True  # Closing animation
        
        # Start animation
        self.animation_progress = 0
        self.is_animating = True
        self.animation_start_time = time.time() * 1000  # Convert to milliseconds
        self.animation_timer.start()

    def _handle_login(self) -> None:
        """Handle login attempt."""
        password = self.password_input.text()
        if not password:
            self.logger.error("No password entered")
            QMessageBox.warning(self, "Fehler", "Bitte Passwort eingeben.")
            return

        if self.kp_handler.open_database(password):
            self.logger.info("KeePass database opened successfully")
            self.logger.info("-" * 80)
            self._credentials = (password, password)  # Store for later use
            self.accept()
        else:
            self.logger.error("Failed to open KeePass database")
            QMessageBox.critical(
                self,
                "Fehler",
                "Fehler beim Öffnen der KeePass-Datenbank. Bitte das Passwort überprüfen.",
            )

    def get_credentials(self) -> Optional[Tuple[str, str]]:
        """Get the entered credentials.
        
        Returns:
            Tuple of (username, password) or None if login failed
        """
        return self._credentials 