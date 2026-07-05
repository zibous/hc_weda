# -*- coding: utf-8 -*-
"""Startup-Logik für hc_weda – ausgelagert aus main.py."""

import json
import logging
from datetime import datetime

from app.core import ha_discovery, mqtt
from app.core.config import APP_NAME, APP_VERSION, HA_BASETOPIC, HA_DISCOVERY_ON
from app.core.webhook import notify_ha
from app.services.device_manager import DeviceManager

logger = logging.getLogger(__name__)


def publish_app_status(status: str, device_manager: DeviceManager = None):
    """Publiziert App-Status via MQTT mit LWT."""
    devices_info = []
    if device_manager:
        devices_info = [
            {"id": d.device_id, "name": d.device_name, "type": d.device_type}
            for d in device_manager.get_all_devices()
        ]

    payload = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": status,
        "devices": devices_info,
        "timestamp": datetime.now().isoformat(),
    }

    topic = f"{HA_BASETOPIC}/status"

    if status == "online":
        lwt_payload = {**payload, "status": "offline"}
        client = mqtt.get_client(
            client_id=f"{APP_NAME}_status",
            lwt_topic=topic,
            lwt_payload=json.dumps(lwt_payload),
        )
        if client:
            try:
                client.publish(topic, json.dumps(payload), retain=True)
                client.disconnect()
                logger.info("App-Status publiziert: %s (mit LWT)", status)
                return
            except Exception as e:
                logger.error("App-Status Publish fehlgeschlagen: %s", e)

    mqtt.publish(topic, payload, retain=True)


def publish_ha_discovery(device_manager: DeviceManager):
    """Publiziert HA MQTT Discovery für alle Geräte."""
    ha_discovery.publish_app_status_sensor()
    logger.info("HA Discovery: App-Status Sensor publiziert")

    for device in device_manager.get_all_devices():
        mqtt_config = device.config.get("mqtt", {})
        base_topic = mqtt_config.get("base_topic", f"{HA_BASETOPIC}/{device.device_type}")

        success = ha_discovery.publish_device_discovery(
            device_id=device.device_id,
            device_name=device.device_name,
            device_type=device.device_type,
            base_topic=base_topic,
        )
        if success:
            logger.info("HA Discovery: %s publiziert", device.device_name)
        else:
            logger.warning("HA Discovery: %s fehlgeschlagen", device.device_name)


def send_app_start(device_manager: DeviceManager):
    """Sendet app_start Webhook."""
    notify_ha(
        "app_start",
        devices_count=len(device_manager.get_all_devices()),
        devices=[
            {"id": d.device_id, "name": d.device_name, "type": d.device_type}
            for d in device_manager.get_all_devices()
        ],
    )
