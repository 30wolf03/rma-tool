"""Centralized login window for the RMA-Tool.

This module provides a unified login interface that can be used across
all modules in the application.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QApplication,
    QFrame,
    QWidget,
)
from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QSize, QTimer
from PySide6.QtGui import QIcon, QFont

from ..utils.logger import setup_logger
from .credential_cache import get_credential_cache, CredentialType


class CentralLoginWindow(QDialog):
    """Centralized login window for KeePass database access and user credentials.
    
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
        self._credentials: Optional[Tuple[str, str]] = None  # (initials, master_password)
        self.credential_cache = get_credential_cache()
        self.is_logging_in = False  # Flag to prevent multiple simultaneous login attempts

        self.setWindowTitle("RMA-Tool - Zentrale Anmeldung")
        self.setGeometry(100, 100, 500, 350)
        self.setFixedSize(500, 350)
        self.logger.info("Initializing central login window")

        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 20, 30, 20)

        # Title label
        title_label = QLabel("RMA-Tool - Zentrale Anmeldung")
        title_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Login Section
        self._create_login_section(layout)

        # Login button
        self.login_button = QPushButton("Anmelden", self)
        self.login_button.setDefault(True)
        self.login_button.setMinimumHeight(38)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 7px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #fb8c00;
            }
            QPushButton:pressed {
                background-color: #ef6c00;
            }
        """)
        self.login_button.clicked.connect(self._handle_login)
        layout.addWidget(self.login_button)

        # Center window
        self._center_window()

    def _create_login_section(self, parent_layout):
        """Create the login section."""
        login_layout = QVBoxLayout()
        login_layout.setSpacing(10)

        # Initials/Kürzel input
        self.initials_input = QLineEdit(self)
        self.initials_input.setPlaceholderText("Kürzel/Initialen eingeben...")
        self.initials_input.setMinimumHeight(36)
        self.initials_input.setFont(QFont("Segoe UI", 11))
        self.initials_input.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #ced4da;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #ff9800;
                outline: none;
            }
        """)
        # Only login button triggers login, no Enter key connections
        # self.initials_input.returnPressed.connect(self._handle_login)
        login_layout.addWidget(self.initials_input)

        # KeePass Master Password input
        pw_row = QHBoxLayout()
        pw_row.setSpacing(6)
        self.master_password_input = QLineEdit(self)
        self.master_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_password_input.setPlaceholderText("KeePass Master-Passwort eingeben...")
        self.master_password_input.setMinimumHeight(36)
        self.master_password_input.setFont(QFont("Segoe UI", 11))
        self.master_password_input.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #ced4da;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #ff9800;
                outline: none;
            }
        """)
        # Only connect login button to handle login, remove Enter key connections
        # self.master_password_input.returnPressed.connect(self._handle_login)
        pw_row.addWidget(self.master_password_input)

        # Toggle password visibility button
        self.show_password_btn = QPushButton(self)
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setFixedSize(36, 36)
        self.show_password_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                border: 1.5px solid #ced4da;
                background: white;
                border-radius: 6px;
                font-size: 15px;
            }
            QPushButton:hover {
                background: #f8f9fa;
                border-color: #ff9800;
            }
        """)
        self.show_password_btn.toggled.connect(self._toggle_password_visibility)
        self.show_password_btn.setText("👁")
        pw_row.addWidget(self.show_password_btn)

        login_layout.addLayout(pw_row)
        parent_layout.addLayout(login_layout)

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
            self.master_password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.is_closing = False  # Opening animation
        else:
            self.logger.info("Password visibility deactivated")
            self.master_password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.is_closing = True  # Closing animation
        
        # Start animation
        self.animation_progress = 0
        self.is_animating = True
        self.animation_start_time = time.time() * 1000  # Convert to milliseconds
        self.animation_timer.start()

    def _handle_login(self) -> None:
        """Handle login attempt."""
        # Prevent multiple simultaneous login attempts
        if self.is_logging_in:
            self.logger.warning("Login attempt already in progress, ignoring duplicate request")
            return

        self.is_logging_in = True
        self.login_button.setEnabled(False)

        try:
            initials = self.initials_input.text().strip()
            master_password = self.master_password_input.text()

            # Validate inputs
            if not initials:
                self.logger.error("No initials entered")
                LoggingMessageBox.warning(self, "Fehler", "Bitte Kürzel/Initialen eingeben.")
                self.initials_input.setFocus()
                return

            if not master_password:
                self.logger.error("No master password entered")
                LoggingMessageBox.warning(self, "Fehler", "Bitte KeePass Master-Passwort eingeben.")
                self.master_password_input.setFocus()
                return

            # Try to open KeePass database
            if self.kp_handler.open_database(master_password):
                self.logger.info("KeePass database opened successfully")
                self.logger.info("-" * 80)

                # Store credentials in cache
                self._store_credentials_in_cache(initials, master_password)

                self._credentials = (initials, master_password)  # Store for later use
                self.accept()
            else:
                self.logger.error("Failed to open KeePass database")
                LoggingMessageBox.critical(self, "Fehler", "Fehler beim Öffnen der KeePass-Datenbank. Bitte das Master-Passwort überprüfen.",)
                self.master_password_input.setFocus()
        finally:
            self.is_logging_in = False
            self.login_button.setEnabled(True)

    def _store_credentials_in_cache(self, initials: str, master_password: str) -> None:
        """Store credentials in the credential cache.
        
        Args:
            initials: User's initials/kürzel
            master_password: KeePass master password
        """
        try:
            # Set KeePass handler in cache
            self.credential_cache.set_keepass_handler(self.kp_handler)
            
            # Store KeePass master password (no expiration for master password)
            self.credential_cache.store_credential(
                CredentialType.KEEPASS_MASTER,
                "master",
                master_password,
                expires_in=None  # Never expires
            )
            
            # Store user credentials (initials + master password)
            self.credential_cache.store_credential(
                CredentialType.USER_LOGIN,
                "current_user",
                master_password,
                metadata={"initials": initials}
            )
            
            # Also store in KeePass handler for backward compatibility
            self.kp_handler.set_user_credentials(initials, master_password)
            
            self.logger.info(f"Credentials stored in cache for user: {initials}")
            
        except Exception as e:
            self.logger.error(f"Failed to store credentials in cache: {e}")

    def get_credentials(self) -> Optional[Tuple[str, str]]:
        """Get the stored credentials.
        
        Returns:
            Tuple of (initials, master_password) or None if not available
        """
        return self._credentials 