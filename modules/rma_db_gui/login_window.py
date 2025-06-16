"""Login-Fenster für die RMA-Datenbank GUI.

Dieses Modul implementiert das Login-Fenster mit Initialen-Validierung
und KeePass-Integration.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, Callable

from loguru import logger

from .database.connection import DatabaseConnection
from .utils.handler_validator import (
    validate_initials_format,
    validate_handler_exists,
    InvalidInitialsError,
    HandlerNotFoundError,
    HandlerValidationError
)
from .utils.keepass_handler import KeePassHandler


class LoginWindow:
    """Login-Fenster mit Initialen-Validierung und KeePass-Integration."""
    
    def __init__(
        self,
        parent: tk.Tk,
        db_connection: DatabaseConnection,
        on_login_success: Callable[[str, str], None]
    ):
        """Initialisiert das Login-Fenster.
        
        Args:
            parent: Das Parent-Fenster
            db_connection: Die Datenbankverbindung
            on_login_success: Callback-Funktion bei erfolgreichem Login
        """
        self.parent = parent
        self.db_connection = db_connection
        self.on_login_success = on_login_success
        
        # KeePass-Handler initialisieren
        self.keepass = KeePassHandler()
        
        # Fenster-Einstellungen
        self.window = tk.Toplevel(parent)
        self.window.title("RMA-DB Login")
        self.window.geometry("300x200")
        self.window.resizable(False, False)
        
        # Zentriere das Fenster
        self.window.transient(parent)
        self.window.grab_set()
        
        # UI-Elemente
        self._create_widgets()
        self._center_window()
        
    def _create_widgets(self):
        """Erstellt die UI-Elemente des Login-Fensters."""
        # Hauptframe
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Initialen-Eingabe
        ttk.Label(
            main_frame,
            text="Bitte geben Sie Ihre Initialen ein:"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        self.initials_var = tk.StringVar()
        self.initials_entry = ttk.Entry(
            main_frame,
            textvariable=self.initials_var,
            width=20
        )
        self.initials_entry.grid(
            row=1,
            column=0,
            columnspan=2,
            pady=(0, 20)
        )
        self.initials_entry.focus()
        
        # Login-Button
        ttk.Button(
            main_frame,
            text="Login",
            command=self._handle_login
        ).grid(row=2, column=0, columnspan=2)
        
        # Enter-Taste binden
        self.window.bind('<Return>', lambda e: self._handle_login())
        
    def _center_window(self):
        """Zentriert das Login-Fenster auf dem Bildschirm."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
    def _handle_login(self):
        """Behandelt den Login-Versuch."""
        try:
            # Initialen validieren
            initials = self.initials_var.get().strip()
            initials, name = validate_handler_exists(
                self.db_connection,
                initials
            )
            
            # KeePass-Validierung
            if not self.keepass.validate_credentials(initials):
                messagebox.showerror(
                    "Login fehlgeschlagen",
                    "Ungültige Initialen oder keine Berechtigung"
                )
                return
                
            # Login erfolgreich
            logger.info(f"Erfolgreicher Login für Handler: {name} ({initials})")
            self.window.destroy()
            self.on_login_success(initials, name)
            
        except InvalidInitialsError as e:
            messagebox.showerror("Ungültige Initialen", str(e))
            self.initials_entry.focus()
            
        except HandlerNotFoundError as e:
            messagebox.showerror("Handler nicht gefunden", str(e))
            self.initials_entry.focus()
            
        except HandlerValidationError as e:
            messagebox.showerror("Validierungsfehler", str(e))
            logger.error(f"Handler-Validierungsfehler: {e}")
            
        except Exception as e:
            messagebox.showerror(
                "Fehler",
                "Ein unerwarteter Fehler ist aufgetreten"
            )
            logger.exception(f"Unerwarteter Login-Fehler: {e}")
            
    def show(self):
        """Zeigt das Login-Fenster an."""
        self.window.deiconify()
        self.window.wait_window() 