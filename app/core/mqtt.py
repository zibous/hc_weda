# -*- coding: utf-8 -*-
"""
MQTT Client
============
Wrapper fuer paho-mqtt mit graceful degradation.
Wenn Broker nicht erreichbar, wird ohne Fehler weitergearbeitet.
"""

import json
import socket

import paho.mqtt.client as mqtt

from app.core.config import MQTT_BROKER, MQTT_PASS, MQTT_PORT, MQTT_USER
from app.core.logging import setup_logger

log = setup_logger("mqtt")


def is_broker_reachable() -> bool:
    """Prueft ob MQTT Broker per TCP erreichbar ist (2s Timeout)."""
    try:
        with socket.create_connection((MQTT_BROKER, MQTT_PORT), timeout=2):
            return True
    except OSError:
        return False


def get_client(client_id: str = "", lwt_topic: str = "", lwt_payload: str = "") -> mqtt.Client | None:
    """Erstellt MQTT Client. Gibt None zurueck wenn Broker nicht erreichbar.
    
    Args:
        client_id: Client-ID (optional)
        lwt_topic: Last Will Testament Topic (optional)
        lwt_payload: Last Will Testament Payload (optional)
    """
    if not is_broker_reachable():
        log.warning("MQTT Broker nicht erreichbar: %s:%s", MQTT_BROKER, MQTT_PORT)
        return None

    client = mqtt.Client(client_id=client_id)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    # Last Will Testament setzen (wird bei ungraceful disconnect gesendet)
    if lwt_topic and lwt_payload:
        client.will_set(lwt_topic, lwt_payload, qos=1, retain=True)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        return client
    except Exception as e:
        log.error("MQTT Verbindung fehlgeschlagen: %s", e)
        return None


def publish(topic: str, payload: dict | str, retain: bool = True) -> bool:
    """Publiziert eine Nachricht. Gibt True bei Erfolg zurueck."""
    client = get_client()
    if client is None:
        return False

    try:
        msg = json.dumps(payload) if isinstance(payload, dict) else payload
        result = client.publish(topic, msg, retain=retain)
        result.wait_for_publish(timeout=5)
        client.disconnect()
        log.debug("Published: %s", topic)
        return True
    except Exception as e:
        log.error("Publish fehlgeschlagen [%s]: %s", topic, e)
        return False
