# -*- coding: utf-8 -*-
"""
Open-Meteo Wetter-Vorhersage.

Holt stündliche Vorhersagedaten von der Open-Meteo API.
Dokumentation: https://open-meteo.com/en/docs

Kein API-Key erforderlich.
Rate-Limit (kostenlos): 10.000 Requests/Tag.
Mit 30-Min-Cache: max. 48 Requests/Tag → kein Problem.
"""

import time
import threading
import requests

from app.core.logging import setup_logger

logger = setup_logger("forecast")

# Cache
_cache: dict = {}
_cache_time: float = 0
_cache_lock = threading.Lock()
CACHE_TTL = 1800  # 30 Minuten

# Rate-Limit-Schutz: nach einem 429 warten wir mindestens so lange
_backoff_until: float = 0
BACKOFF_SECONDS = 300  # 5 Minuten Pause nach 429


def fetch_forecast(
    latitude: float = 47.1410,  # Vaduz
    longitude: float = 9.5209,
    hours: int = 48,
) -> dict:
    """Holt stündliche Vorhersage von Open-Meteo.

    - 30-Minuten-Cache verhindert unnötige API-Calls
    - Thread-Lock verhindert parallele Requests bei Cache-Miss
    - Backoff bei HTTP 429 (Rate-Limit)
    - Bei Fehler: letzten Cache zurückgeben

    Returns:
        dict mit 'hourly' Zeitreihen und 'current' Werten.
        Bei Fehler: letzter Cache oder leeres dict.
    """
    global _cache, _cache_time, _backoff_until

    now = time.time()

    # Cache gültig → sofort zurückgeben
    if _cache and (now - _cache_time) < CACHE_TTL:
        return _cache

    # Backoff aktiv → alten Cache zurückgeben
    if now < _backoff_until:
        logger.debug("Forecast: Backoff aktiv, Cache verwenden")
        return _cache if _cache else {}

    # Lock: nur ein Thread holt gleichzeitig neue Daten
    if not _cache_lock.acquire(blocking=False):
        # Anderer Thread holt gerade → alten Cache verwenden
        return _cache if _cache else {}

    try:
        # Nochmal prüfen (anderer Thread könnte Cache gerade gefüllt haben)
        if _cache and (time.time() - _cache_time) < CACHE_TTL:
            return _cache

        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join([
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation_probability",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m",
                    "cloud_cover",
                    "pressure_msl",
                    "uv_index",
                ]),
                "current": ",".join([
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "cloud_cover",
                    "pressure_msl",
                ]),
                "timezone": "Europe/Berlin",
                "forecast_hours": hours,
            },
            timeout=10,
        )

        # Rate-Limit erreicht
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", BACKOFF_SECONDS))
            _backoff_until = time.time() + retry_after
            logger.warning("Open-Meteo Rate-Limit erreicht, Pause %d s", retry_after)
            return _cache if _cache else {}

        resp.raise_for_status()
        data = resp.json()

        result = _transform(data)
        _cache = result
        _cache_time = time.time()
        logger.debug("Vorhersage aktualisiert: %d Stunden", hours)
        return result

    except requests.RequestException as e:
        logger.warning("Open-Meteo Fehler: %s", e)
        return _cache if _cache else {}

    finally:
        _cache_lock.release()


def _transform(raw: dict) -> dict:
    """Transformiert die Open-Meteo Antwort in ein kompaktes Format."""
    result: dict = {"current": {}, "hourly": [], "units": {}}

    current = raw.get("current", {})
    result["current"] = {
        "temp": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "feelsLike": current.get("apparent_temperature"),
        "precipitation": current.get("precipitation"),
        "weatherCode": current.get("weather_code"),
        "weatherText": _wmo_text(current.get("weather_code")),
        "weatherIcon": _wmo_icon(current.get("weather_code")),
        "windSpeed": current.get("wind_speed_10m"),
        "windDir": current.get("wind_direction_10m"),
        "cloudCover": current.get("cloud_cover"),
        "pressure": current.get("pressure_msl"),
    }

    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    for i, t in enumerate(times):
        result["hourly"].append({
            "time": t,
            "temp": _get_idx(hourly, "temperature_2m", i),
            "humidity": _get_idx(hourly, "relative_humidity_2m", i),
            "feelsLike": _get_idx(hourly, "apparent_temperature", i),
            "precipProb": _get_idx(hourly, "precipitation_probability", i),
            "precip": _get_idx(hourly, "precipitation", i),
            "weatherCode": _get_idx(hourly, "weather_code", i),
            "weatherText": _wmo_text(_get_idx(hourly, "weather_code", i)),
            "weatherIcon": _wmo_icon(_get_idx(hourly, "weather_code", i)),
            "windSpeed": _get_idx(hourly, "wind_speed_10m", i),
            "windDir": _get_idx(hourly, "wind_direction_10m", i),
            "windGusts": _get_idx(hourly, "wind_gusts_10m", i),
            "cloudCover": _get_idx(hourly, "cloud_cover", i),
            "pressure": _get_idx(hourly, "pressure_msl", i),
            "uvIndex": _get_idx(hourly, "uv_index", i),
        })

    return result


def _get_idx(data: dict, key: str, idx: int):
    arr = data.get(key, [])
    return arr[idx] if idx < len(arr) else None


_WMO_CODES = {
    0: "Klar", 1: "Überwiegend klar", 2: "Teilweise bewölkt", 3: "Bewölkt",
    45: "Nebel", 48: "Reifnebel",
    51: "Leichter Nieselregen", 53: "Mäßiger Nieselregen", 55: "Starker Nieselregen",
    56: "Gefrierender Nieselregen", 57: "Starker gefr. Nieselregen",
    61: "Leichter Regen", 63: "Mäßiger Regen", 65: "Starker Regen",
    66: "Gefrierender Regen", 67: "Starker gefr. Regen",
    71: "Leichter Schneefall", 73: "Mäßiger Schneefall", 75: "Starker Schneefall",
    77: "Schneegriesel",
    80: "Leichte Regenschauer", 81: "Mäßige Regenschauer", 82: "Starke Regenschauer",
    85: "Leichte Schneeschauer", 86: "Starke Schneeschauer",
    95: "Gewitter", 96: "Gewitter mit leichtem Hagel", 99: "Gewitter mit starkem Hagel",
}

_WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️", 56: "🌧️", 57: "🌧️",
    61: "🌦️", 63: "🌧️", 65: "🌧️", 66: "🌧️", 67: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️", 77: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    85: "🌨️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

def _wmo_text(code) -> str:
    if code is None:
        return ""
    return _WMO_CODES.get(int(code), f"Code {code}")

def _wmo_icon(code) -> str:
    if code is None:
        return ""
    return _WMO_ICONS.get(int(code), "🌡️")
