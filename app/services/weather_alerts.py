# -*- coding: utf-8 -*-
"""
Wetter-Warnsystem
=================
Überwacht Wetterdaten und sendet Warnungen via Webhook an Home Assistant.

Warnungen:
  - Sturm: Windgeschwindigkeit > 50 km/h oder Böen > 70 km/h
  - Starkregen: Regenrate > 10 mm/h
  - Frost: Temperatur <= 0°C
  - Gefrieren: Temperatur <= 3°C (Frostgefahr)
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from app.core.logging import setup_logger
from app.core.webhook import notify_ha
from app.models.weather import WeatherReading

log = setup_logger("weather_alerts")


class WeatherAlerts:
    """Wetter-Warnsystem mit Hysterese (verhindert Flapping)."""

    def __init__(self):
        # Aktive Warnungen (key: alert_type, value: timestamp)
        self.active_alerts: Dict[str, datetime] = {}
        
        # Schwellwerte
        self.thresholds = {
            "storm_wind": 50.0,      # km/h
            "storm_gust": 70.0,      # km/h
            "heavy_rain": 10.0,      # mm/h
            "frost": 0.0,            # °C
            "freeze_risk": 3.0,      # °C
        }
        
        # Hysterese: Warnung bleibt mindestens X Minuten aktiv
        self.min_alert_duration = timedelta(minutes=15)
        
        # Cooldown: Nach Deaktivierung mindestens X Minuten warten
        self.cooldown_duration = timedelta(minutes=5)
        self.cooldown: Dict[str, datetime] = {}

    def check_alerts(self, reading: WeatherReading) -> None:
        """Prüft Wetterdaten und sendet Warnungen.
        
        Args:
            reading: Aktuelle Wetterdaten
        """
        now = datetime.now()
        
        # Sturm-Warnung (Wind oder Böen)
        storm_active = (
            (reading.wind_speed_kmh or 0) > self.thresholds["storm_wind"] or
            (reading.wind_gust_kmh or 0) > self.thresholds["storm_gust"]
        )
        self._handle_alert(
            "storm",
            storm_active,
            now,
            message=f"Sturm! Wind: {reading.wind_speed_kmh:.1f} km/h, Böen: {reading.wind_gust_kmh:.1f} km/h",
            severity="warning",
            wind_kmh=reading.wind_speed_kmh,
            gust_kmh=reading.wind_gust_kmh,
        )
        
        # Starkregen-Warnung
        heavy_rain_active = (reading.rain_rate_mmh or 0) > self.thresholds["heavy_rain"]
        self._handle_alert(
            "heavy_rain",
            heavy_rain_active,
            now,
            message=f"Starkregen! {reading.rain_rate_mmh:.1f} mm/h",
            severity="warning",
            rain_rate_mmh=reading.rain_rate_mmh,
        )
        
        # Frost-Warnung (≤ 0°C)
        frost_active = (reading.temp_c or 99) <= self.thresholds["frost"]
        self._handle_alert(
            "frost",
            frost_active,
            now,
            message=f"Frost! Temperatur: {reading.temp_c:.1f}°C",
            severity="warning",
            temp_c=reading.temp_c,
        )
        
        # Frostgefahr-Warnung (≤ 3°C, aber > 0°C)
        freeze_risk_active = (
            self.thresholds["frost"] < (reading.temp_c or 99) <= self.thresholds["freeze_risk"]
        )
        self._handle_alert(
            "freeze_risk",
            freeze_risk_active,
            now,
            message=f"Frostgefahr! Temperatur: {reading.temp_c:.1f}°C",
            severity="info",
            temp_c=reading.temp_c,
        )

    def _handle_alert(
        self,
        alert_type: str,
        condition_met: bool,
        now: datetime,
        message: str,
        severity: str,
        **kwargs,
    ) -> None:
        """Verwaltet eine Warnung mit Hysterese und Cooldown.
        
        Args:
            alert_type: Typ der Warnung (z.B. "storm", "frost")
            condition_met: True wenn Schwellwert überschritten
            now: Aktueller Zeitpunkt
            message: Warnmeldung
            severity: "info", "warning", "critical"
            **kwargs: Zusätzliche Daten für Webhook
        """
        is_active = alert_type in self.active_alerts
        in_cooldown = alert_type in self.cooldown and now < self.cooldown[alert_type]
        
        if condition_met:
            # Bedingung erfüllt
            if not is_active and not in_cooldown:
                # Neue Warnung aktivieren
                self.active_alerts[alert_type] = now
                self._send_alert(alert_type, "on", message, severity, **kwargs)
                log.info("Warnung aktiviert: %s", alert_type)
        else:
            # Bedingung nicht erfüllt
            if is_active:
                # Prüfe ob Mindestdauer erreicht
                alert_start = self.active_alerts[alert_type]
                if now - alert_start >= self.min_alert_duration:
                    # Warnung deaktivieren
                    del self.active_alerts[alert_type]
                    self.cooldown[alert_type] = now + self.cooldown_duration
                    self._send_alert(alert_type, "off", f"{alert_type.replace('_', ' ').title()} beendet", "info", **kwargs)
                    log.info("Warnung deaktiviert: %s", alert_type)

    def _send_alert(
        self,
        alert_type: str,
        state: str,
        message: str,
        severity: str,
        **kwargs,
    ) -> None:
        """Sendet Warnung via Webhook.
        
        Args:
            alert_type: Typ der Warnung
            state: "on" oder "off"
            message: Warnmeldung
            severity: "info", "warning", "critical"
            **kwargs: Zusätzliche Daten
        """
        try:
            notify_ha(
                "weather_alert",
                alert_type=alert_type,
                state=state,
                message=message,
                severity=severity,
                timestamp=datetime.now().isoformat(),
                **kwargs,
            )
        except Exception as e:
            log.error("Fehler beim Senden der Warnung: %s", e)

    def get_active_alerts(self) -> Dict[str, datetime]:
        """Gibt aktive Warnungen zurück."""
        return self.active_alerts.copy()

    def clear_all_alerts(self) -> None:
        """Löscht alle aktiven Warnungen (z.B. beim App-Start)."""
        for alert_type in list(self.active_alerts.keys()):
            self._send_alert(alert_type, "off", f"{alert_type.replace('_', ' ').title()} zurückgesetzt", "info")
        self.active_alerts.clear()
        self.cooldown.clear()
        log.info("Alle Warnungen zurückgesetzt")
