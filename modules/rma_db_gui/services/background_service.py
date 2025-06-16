"""Hintergrund-Service für regelmäßige Tracking-Updates.

Dieser Service führt regelmäßige Updates der Tracking-Status durch
und kann als Hintergrund-Prozess laufen.
"""

from __future__ import annotations

import asyncio
import signal
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from .tracking_service import DHLTrackingService


class BackgroundService:
    """Hintergrund-Service für regelmäßige Updates."""

    def __init__(
        self,
        tracking_service: DHLTrackingService,
        update_interval: int = 300  # 5 Minuten
    ) -> None:
        """Initialisiert den Hintergrund-Service.
        
        Args:
            tracking_service: DHL-Tracking-Service
            update_interval: Update-Intervall in Sekunden
        """
        self.tracking_service = tracking_service
        self.update_interval = update_interval
        self._running = False
        self._last_update: Optional[datetime] = None

    async def _update_loop(self) -> None:
        """Hauptschleife für regelmäßige Updates."""
        while self._running:
            try:
                logger.debug("Starte Tracking-Update...")
                self.tracking_service.update_all_active_shipments()
                self._last_update = datetime.now()
                logger.debug("Tracking-Update abgeschlossen")
            except Exception as e:
                logger.error("Fehler im Update-Loop: {}", e)
            
            # Warte bis zum nächsten Update
            await asyncio.sleep(self.update_interval)

    def start(self) -> None:
        """Startet den Hintergrund-Service."""
        if self._running:
            logger.warning("Service läuft bereits")
            return

        self._running = True
        logger.info("Starte Hintergrund-Service...")

        # Event-Loop erstellen und starten
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Signal-Handler für sauberes Beenden
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        try:
            loop.run_until_complete(self._update_loop())
        except Exception as e:
            logger.error("Fehler im Event-Loop: {}", e)
        finally:
            loop.close()

    async def stop(self) -> None:
        """Stoppt den Hintergrund-Service."""
        if not self._running:
            return

        logger.info("Stoppe Hintergrund-Service...")
        self._running = False

        # Warte auf laufende Updates
        if self._last_update:
            time_since_update = datetime.now() - self._last_update
            if time_since_update < timedelta(seconds=self.update_interval):
                logger.debug("Warte auf Abschluss des laufenden Updates...")
                await asyncio.sleep(1)  # Kurze Wartezeit für laufende Updates

        logger.info("Hintergrund-Service gestoppt") 