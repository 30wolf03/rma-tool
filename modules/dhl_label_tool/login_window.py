from shared.utils.enhanced_logging import LoggingMessageBox, log_error_and_show_dialog
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QApplication
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QSize, QTimer
from PySide6.QtGui import QIcon
import time
from shared.utils.enhanced_logging import get_module_logger
from icons import get_eye_icon, svg_to_pixmap, create_animated_svg


class LoginWindow(QDialog):
    def __init__(self, kp_handler, parent=None):
        super().__init__(parent)
        self.logger = get_module_logger("LoginWindow")
        self.kp_handler = kp_handler

        self.setWindowTitle("KeePass Login")
        self.setGeometry(100, 100, 300, 150)
        self.logger.info("Initialisiere Login-Fenster")

        layout = QVBoxLayout(self)

        # Label für die Passwortabfrage
        self.label = QLabel(
            "Bitte das Master-Passwort für die KeePass-Datenbank eingeben:"
        )
        layout.addWidget(self.label)

        # Horizontales Layout für das Passwortfeld und den Toggle-Button
        password_layout = QHBoxLayout()
        self.keepass_master_password_input = QLineEdit(self)
        self.keepass_master_password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.keepass_master_password_input)

        # Toggle-Button mit Icon
        self.show_password_btn = QPushButton(self)
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setFixedSize(30, 30)
        self.show_password_btn.setFocusPolicy(Qt.NoFocus)
        self.show_password_btn.setIcon(get_eye_icon(False))
        self.show_password_btn.setIconSize(QSize(20, 20))
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background: #e0e0e0;
            }
        """)
        self.show_password_btn.toggled.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)

        layout.addLayout(password_layout)

        # Login-Button
        self.login_button = QPushButton("Login", self)
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)

        # Fenster zentrieren
        self.center_window()

        # Animation-Timer
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(16)  # ~60 FPS
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_progress = 0
        self.is_animating = False
        self.animation_duration = 300  # 300ms Gesamtdauer
        self.animation_start_time = 0
        self.is_closing = True  # Richtung der Animation

    def center_window(self):
        """Zentriert das Fenster auf dem Bildschirm."""
        screen = QApplication.primaryScreen()
        screen_center = screen.availableGeometry().center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

    def update_animation(self):
        """Aktualisiert die Icon-Animation."""
        current_time = time.time() * 1000  # Konvertiere zu Millisekunden
        elapsed = current_time - self.animation_start_time
        
        if elapsed >= self.animation_duration:
            self.animation_timer.stop()
            self.is_animating = False
            # Setze das finale Icon
            self.show_password_btn.setIcon(get_eye_icon(self.show_password_btn.isChecked()))
            return

        # Berechne den aktuellen Animationsfortschritt (0.0 bis 1.0)
        progress = elapsed / self.animation_duration
        
        # Erstelle das animierte SVG
        svg = create_animated_svg(progress, self.is_closing)
        
        # Aktualisiere das Icon
        pixmap = svg_to_pixmap(svg)
        self.show_password_btn.setIcon(QIcon(pixmap))

    def toggle_password_visibility(self, checked):
        # Passwort-Sichtbarkeit sofort ändern
        if checked:
            self.logger.info("Passwort-Sichtbarkeit aktiviert")
            self.keepass_master_password_input.setEchoMode(QLineEdit.Normal)
            self.is_closing = False  # Öffnende Animation
        else:
            self.logger.info("Passwort-Sichtbarkeit deaktiviert")
            self.keepass_master_password_input.setEchoMode(QLineEdit.Password)
            self.is_closing = True  # Schließende Animation
        
        # Starte die Animation
        self.animation_progress = 0
        self.is_animating = True
        self.animation_start_time = time.time() * 1000  # Konvertiere zu Millisekunden
        self.animation_timer.start()

    def handle_login(self):
        keepass_master_password = self.keepass_master_password_input.text()
        if not keepass_master_password:
            self.logger.error("Kein Passwort eingegeben")
            LoggingMessageBox.warning(self, "Fehler", "Bitte Passwort eingeben.")
            return

        if self.kp_handler.open_database(keepass_master_password):
            self.logger.info("KeePass-Datenbank erfolgreich geöffnet")
            self.logger.info("-" * 80)
            self.accept()
        else:
            self.logger.error("Fehler beim Öffnen der KeePass-Datenbank")
            LoggingMessageBox.critical(self, "Fehler", "Fehler beim Öffnen der KeePass-Datenbank. Bitte das Passwort überprüfen.",)
