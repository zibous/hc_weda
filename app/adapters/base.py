# -*- coding: utf-8 -*-
"""
Basis-Adapter für Datenquellen
==============================
Abstrakte Klasse, die das Interface für alle Geräte-Adapter definiert.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union

from app.models.weather import DeviceInfo, WeatherReading


class DatasourceAdapter(ABC):
    """Abstrakte Basisklasse für Geräte-Adapter.

    Jeder Adapter muss:
    - fetch_reading(): Einen normalisierten WeatherReading liefern
    - fetch_device_info(): Geräteinformationen liefern
    - is_reachable(): Erreichbarkeit prüfen
    """

    def __init__(self, config: dict):
        """Initialisiert den Adapter mit der Geräte-Konfiguration.

        Args:
            config: Dict aus der YAML-Gerätekonfiguration
        """
        self.config = config
        self.device_name = config.get("device", {}).get("name", "Unknown")
        self.device_type = config.get("device", {}).get("type", "unknown")
        self.device_id = config.get("device", {}).get("device_id", "")

    @abstractmethod
    def fetch_reading(self) -> Optional[WeatherReading]:
        """Holt einen aktuellen Messwert vom Gerät.

        Returns:
            WeatherReading oder None bei Fehler
        """
        ...

    @abstractmethod
    def fetch_device_info(self) -> Optional[DeviceInfo]:
        """Holt Geräteinformationen.

        Returns:
            DeviceInfo oder None bei Fehler
        """
        ...

    @abstractmethod
    def is_reachable(self) -> bool:
        """Prüft ob das Gerät erreichbar ist.

        Returns:
            True wenn erreichbar
        """
        ...
