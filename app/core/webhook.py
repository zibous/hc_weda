# -*- coding: utf-8 -*-
"""
Webhook-Modul für Home Assistant Benachrichtigungen
====================================================
Sendet Events an Home Assistant via Webhook.

Events:
  - app_start: App wurde gestartet
  - app_stop: App wurde gestoppt
  - device_online: Gerät ist online
  - device_offline: Gerät ist offline
  - error: Fehler aufgetreten
"""

from typing import Any, Dict, Optional

import requests

from app.core.logging import setup_logger

log = setup_logger("webhook")


class Webhook:
    """Home Assistant Webhook Client."""

    def __init__(self, base_url: str, webhook_id: str, timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.webhook_id = webhook_id
        self.timeout = timeout

    @property
    def url(self) -> str:
        """Webhook URL."""
        return f"{self.base_url}/api/webhook/{self.webhook_id}"

    def send(self, data: Optional[Dict[str, Any]] = None) -> bool:
        """Sendet Daten an Webhook. Gibt True bei Erfolg zurück."""
        try:
            response = requests.post(self.url, json=data or {}, timeout=self.timeout)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            log.debug("Webhook send failed: %s", e)
            return False


_webhook: Optional[Webhook] = None


def _get_webhook() -> Optional[Webhook]:
    """Lazy-init Webhook aus Config."""
    global _webhook
    if _webhook is not None:
        return _webhook

    try:
        from app.core.config import HA_WEBHOOK_ID, HA_WEBHOOK_URL

        if HA_WEBHOOK_URL and HA_WEBHOOK_ID:
            _webhook = Webhook(HA_WEBHOOK_URL, HA_WEBHOOK_ID)
            return _webhook
    except Exception:
        pass

    return None


def notify_ha(event: str, **kwargs: Any) -> bool:
    """Sendet ein Event an Home Assistant (wenn konfiguriert).
    
    Args:
        event: Event-Name (z.B. "app_start", "device_online", "error")
        **kwargs: Zusätzliche Event-Daten
    
    Returns:
        True bei Erfolg, False wenn Webhook nicht konfiguriert oder Fehler
    
    Beispiele:
        notify_ha("app_start", version="1.0.0", devices=2)
        notify_ha("device_online", device_id="ISk5MT174-0001", device_name="Tasmota")
        notify_ha("error", message="Connection timeout", severity="warning")
    """
    wh = _get_webhook()
    if not wh:
        return False

    try:
        from datetime import datetime

        from app.core.config import APP_NAME, APP_VERSION

        payload: Dict[str, Any] = {
            "event": event,
            "app": APP_NAME,
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(),
        }
        payload.update(kwargs)

        ok = wh.send(payload)
        if ok:
            log.debug("Webhook sent: %s", event)
        return ok
    except Exception as e:
        log.debug("Webhook error: %s", e)
        return False
