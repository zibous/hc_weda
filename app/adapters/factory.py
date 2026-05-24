# -*- coding: utf-8 -*-
"""
Adapter Factory
===============
Erstellt den passenden Adapter basierend auf dem Gerätetyp in der YAML-Config.
"""

from app.adapters.base import DatasourceAdapter
from app.adapters.sainlogic_ws3500 import SainlogicWS3500Adapter
from app.core.logging import setup_logger

log = setup_logger("adapter.factory")

# Registry: device_type -> Adapter-Klasse
_ADAPTER_REGISTRY: dict[str, type[DatasourceAdapter]] = {
    "sainlogic-ws3500": SainlogicWS3500Adapter,
}


def create_adapter(config: dict) -> DatasourceAdapter:
    """Erstellt einen Adapter basierend auf der Geräte-Konfiguration.

    Args:
        config: Dict aus der YAML-Gerätekonfiguration

    Returns:
        Passender DatasourceAdapter

    Raises:
        ValueError: Wenn der Gerätetyp unbekannt ist
    """
    device_type = config.get("device", {}).get("type", "")

    if device_type not in _ADAPTER_REGISTRY:
        available = ", ".join(_ADAPTER_REGISTRY.keys())
        raise ValueError(
            f"Unbekannter Gerätetyp: '{device_type}'. "
            f"Verfügbar: {available}"
        )

    adapter_class = _ADAPTER_REGISTRY[device_type]
    adapter = adapter_class(config)
    log.info("Adapter erstellt: %s (%s)", adapter.device_name, device_type)
    return adapter
