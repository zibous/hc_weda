# -*- coding: utf-8 -*-
"""
Home Assistant MQTT Discovery
===============================
Registriert Sensoren automatisch in Home Assistant.
"""

from app.core.config import APP_NAME, APP_VERSION, HA_BASETOPIC, HA_DISCOVERY
from app.core.logging import setup_logger
from app.core.mqtt import publish

log = setup_logger("ha_discovery")


def get_device_info(device_id: str = "hc_weda", device_name: str = "hc_weda") -> dict:
    """Erstellt Device-Info für HA Discovery."""
    return {
        "identifiers": [device_id],
        "name": device_name,
        "manufacturer": "SmartHome",
        "model": "Weather Station Monitor",
        "sw_version": APP_VERSION,
    }


def publish_device_discovery(
    device_id: str,
    device_name: str,
    device_type: str,
    base_topic: str,
) -> bool:
    """Publiziert Discovery-Messages für ein Gerät.
    Erstellt Sensoren für:
    - Gesamtbezug (kWh)
    - Gesamteinspeisung (kWh)
    - Aktuelle Leistung (W) - nur P1 Meter
    - Spannung/Frequenz - nur P1 Meter
    """
    device_info = get_device_info(device_id, device_name)
    success = True

    # Basis-Sensoren (für alle Geräte)
    sensors = [
        {
            "key": "gesamt_bezug_kwh",
            "name": f"{device_name} Gesamtbezug",
            "unit": "kWh",
            "icon": "mdi:transmission-tower-import",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
        {
            "key": "gesamt_einspeisung_kwh",
            "name": f"{device_name} Gesamteinspeisung",
            "unit": "kWh",
            "icon": "mdi:transmission-tower-export",
            "device_class": "energy",
            "state_class": "total_increasing",
        },
    ]

    # Tasmota-spezifische Sensoren
    if device_type == "tasmota":
        sensors.extend([
            {
                "key": "bezug_ht_kwh",
                "name": f"{device_name} Bezug HT",
                "unit": "kWh",
                "icon": "mdi:counter",
                "device_class": "energy",
                "state_class": "total_increasing",
            },
            {
                "key": "bezug_nt_kwh",
                "name": f"{device_name} Bezug NT",
                "unit": "kWh",
                "icon": "mdi:counter",
                "device_class": "energy",
                "state_class": "total_increasing",
            },
        ])

    # P1 Meter-spezifische Sensoren
    if device_type == "homewizard-p1":
        sensors.extend([
            {
                "key": "leistung_w",
                "name": f"{device_name} Leistung",
                "unit": "W",
                "icon": "mdi:flash",
                "device_class": "power",
                "state_class": "measurement",
            },
            {
                "key": "spannung_l1_v",
                "name": f"{device_name} Spannung L1",
                "unit": "V",
                "icon": "mdi:sine-wave",
                "device_class": "voltage",
                "state_class": "measurement",
            },
            {
                "key": "frequenz_hz",
                "name": f"{device_name} Frequenz",
                "unit": "Hz",
                "icon": "mdi:waveform",
                "device_class": "frequency",
                "state_class": "measurement",
            },
        ])

    # Publiziere alle Sensoren
    for sensor in sensors:
        unique_id = f"{device_id}_{sensor['key']}"
        config_topic = f"{HA_DISCOVERY}/sensor/{device_id}/{sensor['key']}/config"

        payload = {
            "name": sensor["name"],
            "unique_id": unique_id,
            "state_topic": f"{base_topic}/data",
            "value_template": f"{{{{ value_json.{sensor['key']} }}}}",
            "device": device_info,
        }

        if sensor.get("unit"):
            payload["unit_of_measurement"] = sensor["unit"]
        if sensor.get("icon"):
            payload["icon"] = sensor["icon"]
        if sensor.get("device_class"):
            payload["device_class"] = sensor["device_class"]
        if sensor.get("state_class"):
            payload["state_class"] = sensor["state_class"]

        if not publish(config_topic, payload, retain=True):
            log.warning("Discovery fehlgeschlagen: %s", sensor["name"])
            success = False
        else:
            log.debug("Discovery publiziert: %s", sensor["name"])

    return success


def publish_app_status_sensor() -> bool:
    """Publiziert Discovery für App-Status Sensor."""
    device_info = get_device_info("hc_weda", APP_NAME)
    config_topic = f"{HA_DISCOVERY}/sensor/hc_weda/status/config"

    payload = {
        "name": f"{APP_NAME} Status",
        "unique_id": "hc_weda_status",
        "state_topic": f"{HA_BASETOPIC}/status",
        "value_template": "{{ value_json.status }}",
        "icon": "mdi:server",
        "device": device_info,
    }

    return publish(config_topic, payload, retain=True)


def remove_device_discovery(device_id: str, device_type: str) -> bool:
    """Entfernt Discovery-Messages für ein Gerät."""
    # Liste aller möglichen Sensor-Keys
    keys = [
        "gesamt_bezug_kwh",
        "gesamt_einspeisung_kwh",
        "bezug_ht_kwh",
        "bezug_nt_kwh",
        "leistung_w",
        "spannung_l1_v",
        "frequenz_hz",
    ]

    success = True
    for key in keys:
        config_topic = f"{HA_DISCOVERY}/sensor/{device_id}/{key}/config"
        if not publish(config_topic, "", retain=True):
            success = False

    return success

