# ecowitt_validator.py

from __future__ import annotations
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import time
from app.core.logging import setup_logger

log = setup_logger("adapter.EcowittValidator")


class EcowittValidator:
    """
    Validiert Ecowitt-Daten sicher und fehlertolerant.
    - Pflichtfelder
    - Typprüfung
    - Wertebereiche
    - KEINE Zeitstempelprüfung mehr
    - Optionale Zeitkorrektur (UTC → Lokal)
    """

    REQUIRED_FIELDS = ["tempf", "humidity", "windspeedmph", "dateutc"]

    def __init__(self, time_correction: bool = False):
        self.time_correction = time_correction

    # ------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------

    def safe_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    def safe_int(self, value: Any) -> Optional[int]:
        try:
            return int(float(value))
        except Exception:
            return None

    def convert_timestamp(self, ts: Optional[str]) -> str:
        """
        Optional: UTC → lokale Zeit konvertieren.
        Gibt IMMER einen String zurück.
        """
        if not ts:
            return ""

        try:
            ts_clean = ts.replace("+", " ")
            dt_utc = datetime.strptime(ts_clean, "%Y-%m-%d %H:%M:%S")

            if not self.time_correction:
                return ts_clean

            # DST automatisch bestimmen
            is_dst = time.localtime().tm_isdst
            offset_hours = 2 if is_dst else 1

            dt_local = dt_utc + timedelta(hours=offset_hours)
            return dt_local.strftime("%Y-%m-%d %H:%M:%S")

        except Exception:
            log.warning("Zeitformat konnte nicht geparst werden: %s", ts)
            return ts  # Roh übernehmen

    # ------------------------------------------------------------
    # Validierungslogik
    # ------------------------------------------------------------

    def validate_required(self, params: Dict[str, Any]) -> bool:
        for key in self.REQUIRED_FIELDS:
            if key not in params:
                log.error("Pflichtfeld fehlt: %s", key)
                return False
        return True

    def validate_ranges(self, data: Dict[str, Any]) -> bool:

        if data["tempf"] is None or not (-40 <= data["tempf"] <= 150):
            log.warning("Ungültige Temperatur: %s", data["tempf"])
            return False

        if data["humidity"] is None or not (0 <= data["humidity"] <= 100):
            log.warning("Ungültige Luftfeuchte: %s", data["humidity"])
            return False

        if data["windspeedmph"] is None or data["windspeedmph"] < 0:
            log.warning("Ungültige Windgeschwindigkeit: %s", data["windspeedmph"])
            return False

        if data["winddir"] is not None and not (0 <= data["winddir"] <= 360):
            log.warning("Ungültige Windrichtung: %s", data["winddir"])
            return False

        if data["uv"] is not None and not (0 <= data["uv"] <= 15):
            log.warning("Ungültiger UV-Index: %s", data["uv"])
            return False

        if data["solarradiation"] is not None and not (0 <= data["solarradiation"] <= 2000):
            log.warning("Ungültige Solarstrahlung: %s", data["solarradiation"])
            return False

        if data["baromin"] is not None and not (25 <= data["baromin"] <= 32):
            log.warning("Ungültiger Luftdruck: %s", data["baromin"])
            return False

        return True

    # ------------------------------------------------------------
    # Hauptfunktion
    # ------------------------------------------------------------

    def extract_raw(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:

        if not self.validate_required(params):
            return None

        timestamp = self.convert_timestamp(params.get("dateutc"))

        raw = {
            "tempf": self.safe_float(params.get("tempf")),
            "humidity": self.safe_int(params.get("humidity")),
            "windspeedmph": self.safe_float(params.get("windspeedmph")),
            "winddir": self.safe_int(params.get("winddir")),
            "uv": self.safe_float(params.get("uv")),
            "solarradiation": self.safe_float(params.get("solarradiation")),
            "baromin": self.safe_float(params.get("baromin")),
            "timestamp": timestamp,
        }

        if not self.validate_ranges(raw):
            return None

        return raw
