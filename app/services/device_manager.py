# -*- coding: utf-8 -*-
"""
Device Manager
==============
Verwaltet Wetterstation-Geräte.

Lädt Geräte-Konfigurationen aus YAML-Dateien und erstellt
für jedes Gerät einen Adapter.
"""

import os
from pathlib import Path
from typing import Optional

import yaml

from app.adapters.base import DatasourceAdapter
from app.adapters.factory import create_adapter
from app.core.config import PATHS
from app.core.logging import setup_logger
from app.services.database import WeatherDB

log = setup_logger("device_manager")


class ManagedDevice:
    """Ein verwaltetes Gerät mit Adapter."""

    def __init__(self, config: dict, db: WeatherDB, data_dir: Path):
        self.config = config
        self.device_name = config.get("device", {}).get("name", "Unknown")
        self.device_type = config.get("device", {}).get("type", "unknown")
        self.device_id = config.get("device", {}).get("device_id", "")

        # Adapter für Datenabfrage
        self.adapter: DatasourceAdapter = create_adapter(config)

        # Polling-Intervall (für HTTP Receiver nicht relevant, aber für Kompatibilität)
        ds_config = config.get("datasource", {})
        self.poll_interval = ds_config.get("interval", 60)

        log.info("Gerät geladen: %s (%s, Intervall: %ds)",
                 self.device_name, self.device_type, self.poll_interval)

    def start_watcher(self):
        """Dummy-Methode für Kompatibilität (keine CSV-Watcher bei Wetterstation)."""
        pass

    def stop_watcher(self):
        """Dummy-Methode für Kompatibilität (keine CSV-Watcher bei Wetterstation)."""
        pass


class DeviceManager:
    """Verwaltet alle konfigurierten Wetterstation-Geräte."""

    def __init__(self, db: WeatherDB, config_dir: Optional[Path] = None,
                 data_dir: Optional[Path] = None):
        self.db = db
        self.config_dir = config_dir or PATHS["config"] / "devices"
        self.data_dir = data_dir or PATHS["data"]
        self.devices: list[ManagedDevice] = []

        self._load_devices()

    def _load_devices(self):
        """Lädt alle Geräte-Konfigurationen aus YAML-Dateien."""
        if not self.config_dir.exists():
            log.warning("Geräte-Config-Verzeichnis nicht gefunden: %s", self.config_dir)
            return

        yaml_files = list(self.config_dir.glob("*.yaml"))
        if not yaml_files:
            log.warning("Keine Geräte-Konfigurationen gefunden in: %s", self.config_dir)
            return

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                if not config or "device" not in config:
                    log.warning("Ungültige Config: %s", yaml_file.name)
                    continue

                # Ersetze ${VAR} Platzhalter mit Umgebungsvariablen
                config = self._expand_env_vars(config)

                # Prüfe ob Gerät aktiviert ist (YAML + .env Override)
                device_config = config.get("device", {})
                device_type = device_config.get("type", "unknown")
                enabled_in_yaml = device_config.get("enabled", True)

                # .env Override: DEVICE_<TYPE>_ENABLED
                env_key = f"DEVICE_{device_type.upper().replace('-', '_')}_ENABLED"
                enabled_in_env = os.getenv(env_key)

                if enabled_in_env is not None:
                    # .env überschreibt YAML
                    is_enabled = enabled_in_env.lower() in ("true", "1", "yes")
                else:
                    # Fallback auf YAML
                    is_enabled = enabled_in_yaml

                if not is_enabled:
                    log.info("Gerät deaktiviert (via %s): %s",
                             "env" if enabled_in_env else "yaml",
                             device_config.get("name", yaml_file.name))
                    continue

                device = ManagedDevice(config, self.db, self.data_dir)
                self.devices.append(device)

            except Exception as e:
                log.error("Fehler beim Laden von %s: %s", yaml_file.name, e)

        log.info("Device Manager: %d Geräte geladen", len(self.devices))

    def _expand_env_vars(self, config: dict) -> dict:
        """Ersetzt ${VAR} und ${VAR:default} Platzhalter rekursiv.
        
        Beispiele:
          ${DEVICE_URL}           -> os.getenv("DEVICE_URL")
          ${DEVICE_URL:http://..} -> os.getenv("DEVICE_URL", "http://..")
        """
        import re

        def _replace(value):
            if isinstance(value, str):
                # Pattern: ${VAR} oder ${VAR:default}
                pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

                def replacer(match):
                    var_name = match.group(1)
                    default = match.group(2) if match.group(2) is not None else ""
                    return os.getenv(var_name, default)

                return re.sub(pattern, replacer, value)
            elif isinstance(value, dict):
                return {k: _replace(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_replace(item) for item in value]
            return value

        return _replace(config)

    def start_all_watchers(self):
        """Startet alle CSV-Watcher."""
        for device in self.devices:
            device.start_watcher()

    def stop_all_watchers(self):
        """Stoppt alle CSV-Watcher."""
        for device in self.devices:
            device.stop_watcher()

    def get_device_by_id(self, device_id: str) -> Optional[ManagedDevice]:
        """Findet ein Gerät anhand der ID."""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None

    def get_devices_by_type(self, device_type: str) -> list[ManagedDevice]:
        """Findet alle Geräte eines bestimmten Typs."""
        return [d for d in self.devices if d.device_type == device_type]

    def get_all_devices(self) -> list[ManagedDevice]:
        """Gibt alle verwalteten Geräte zurück."""
        return self.devices
