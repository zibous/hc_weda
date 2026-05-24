# -*- coding: utf-8 -*-
"""
Internes Wetter-Datenmodell
===========================
Normalisiertes Modell für Wetterstation (Sainlogic WS3500).
Kompatibel mit dem DB-Schema (weather_readings).

Datenquelle: Ecowitt-Protokoll (Fahrenheit, Inches, MPH)
Speicherung: Metrisch (Celsius, mm, km/h)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WeatherReading:
    """Ein einzelner normalisierter Wettermesswert.

    Alle Werte in metrischen Einheiten:
    - Temperatur: Celsius
    - Regen: mm
    - Wind: km/h
    - Druck: hPa
    """

    timestamp: str  # ISO-Format: "2026-05-09T14:30:00"
    date: str       # "2026-05-09"
    time: str       # "14:30:00"

    # --- Temperatur (°C) ---
    temp_c: Optional[float] = None              # Außentemperatur
    temp_f: Optional[float] = None              # Original Fahrenheit
    feels_like_c: Optional[float] = None        # Gefühlte Temperatur
    indoor_temp_c: Optional[float] = None       # Innentemperatur
    dewpoint_c: Optional[float] = None          # Taupunkt
    windchill_c: Optional[float] = None         # Windchill

    # --- Luftfeuchte (%) ---
    humidity: Optional[int] = None              # Außen
    indoor_humidity: Optional[int] = None       # Innen

    # --- Wind ---
    wind_speed_kmh: Optional[float] = None      # Windgeschwindigkeit (km/h)
    wind_speed_mph: Optional[float] = None      # Original MPH
    wind_gust_kmh: Optional[float] = None       # Windböen (km/h)
    wind_dir_deg: Optional[int] = None          # Windrichtung (Grad)
    wind_dir_text: Optional[str] = None         # Windrichtung (Text: N, NO, O, ...)
    beaufort: Optional[int] = None              # Beaufort-Skala (0-12)
    beaufort_text: Optional[str] = None         # Beaufort-Text

    # --- Regen (mm) ---
    rain_rate_mmh: Optional[float] = None       # Regenrate (mm/h)
    rain_daily_mm: Optional[float] = None       # Regen heute
    rain_weekly_mm: Optional[float] = None      # Regen diese Woche
    rain_monthly_mm: Optional[float] = None     # Regen diesen Monat

    # --- Luftdruck (hPa) ---
    pressure_hpa: Optional[float] = None        # Relativer Luftdruck
    pressure_inhg: Optional[float] = None       # Original InHg
    abs_pressure_hpa: Optional[float] = None    # Absoluter Luftdruck

    # --- Solar / UV ---
    solar_radiation: Optional[float] = None     # W/m²
    solar_klux: Optional[float] = None          # Klux (berechnet)
    uv_index: Optional[int] = None              # UV-Index

    # --- Raumklima ---
    temp_diff_c: Optional[float] = None         # Temperatur-Differenz Innen/Außen
    climate_advice: Optional[str] = None        # Lüftungsempfehlung
    frost_text: Optional[str] = None            # Frostwarnung

    # Quelle
    source: str = "sainlogic-ws3500"

    def to_db_row(self) -> dict:
        """Konvertiert zu einem Dict für DB-Insert (weather_readings-Tabelle)."""
        return {
            "timestamp": self.timestamp,
            "date": self.date,
            "time": self.time,
            "temp_c": self.temp_c,
            "temp_f": self.temp_f,
            "feels_like_c": self.feels_like_c,
            "indoor_temp_c": self.indoor_temp_c,
            "dewpoint_c": self.dewpoint_c,
            "windchill_c": self.windchill_c,
            "humidity": self.humidity,
            "indoor_humidity": self.indoor_humidity,
            "wind_speed_kmh": self.wind_speed_kmh,
            "wind_speed_mph": self.wind_speed_mph,
            "wind_gust_kmh": self.wind_gust_kmh,
            "wind_dir_deg": self.wind_dir_deg,
            "wind_dir_text": self.wind_dir_text,
            "beaufort": self.beaufort,
            "beaufort_text": self.beaufort_text,
            "rain_rate_mmh": self.rain_rate_mmh,
            "rain_daily_mm": self.rain_daily_mm,
            "rain_weekly_mm": self.rain_weekly_mm,
            "rain_monthly_mm": self.rain_monthly_mm,
            "pressure_hpa": self.pressure_hpa,
            "pressure_inhg": self.pressure_inhg,
            "abs_pressure_hpa": self.abs_pressure_hpa,
            "solar_radiation": self.solar_radiation,
            "solar_klux": self.solar_klux,
            "uv_index": self.uv_index,
            "temp_diff_c": self.temp_diff_c,
            "climate_advice": self.climate_advice,
            "frost_text": self.frost_text,
            "source": self.source,
        }


@dataclass
class DeviceInfo:
    """Geräteinformationen (Wetterstation)."""

    name: str = ""
    device_type: str = ""           # "sainlogic-ws3500"
    device_id: str = ""
    model: str = ""
    manufacturer: str = ""
    location: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class DeviceStatus:
    """Aktueller Status der Wetterstation."""

    device_id: str = ""
    online: bool = False
    last_reading: Optional[WeatherReading] = None
    last_success: Optional[str] = None  # ISO timestamp
    last_error: Optional[str] = None
    error_count: int = 0
    readings_count: int = 0
