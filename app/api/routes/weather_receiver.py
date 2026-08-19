# -*- coding: utf-8 -*-
"""
Weather Receiver Route
======================
HTTP Endpoint für Wetterstation (Ecowitt-Protokoll).

Die Wetterstation sendet GET-Requests mit Query-Parametern:
  GET /weatherstation?tempf=68.5&humidity=65&windspeedmph=5.2&...

Dieser Endpoint:
1. Empfängt die Daten
2. Verarbeitet sie über den Sainlogic-Adapter
3. Speichert sie in der Datenbank
4. Publiziert sie via MQTT
5. Sendet Webhook an Home Assistant
"""

from typing import Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core import mqtt
from app.core.logging import setup_logger
from app.core.webhook import notify_ha
from app.services.weather_alerts import WeatherAlerts

log = setup_logger("api.weather_receiver")

router = APIRouter()

# Globales Warnsystem (wird beim App-Start initialisiert)
weather_alerts: Optional[WeatherAlerts] = None


def init_weather_alerts():
    """Initialisiert das Warnsystem."""
    global weather_alerts
    if weather_alerts is None:
        weather_alerts = WeatherAlerts()
        log.info("Wetter-Warnsystem initialisiert")


@router.get("/weatherstation")
@router.post("/weatherstation")
async def receive_weather_data(request: Request):
    """Empfängt Wetterdaten von der Sainlogic WS3500 Station.

    Query-Parameter (Ecowitt-Protokoll):
      - tempf: Außentemperatur (°F)
      - humidity: Luftfeuchte (%)
      - windspeedmph: Windgeschwindigkeit (MPH)
      - winddir: Windrichtung (Grad)
      - rainin: Regenrate (Inch/h)
      - dailyrainin: Regen heute (Inch)
      - baromin: Luftdruck (InHg)
      - UV: UV-Index
      - solarradiation: Solar-Strahlung (W/m²)
      - indoortempf: Innentemperatur (°F)
      - indoorhumidity: Innen-Luftfeuchte (%)
      - dateutc: Zeitstempel (UTC)

    Returns:
        JSON mit verarbeiteten Wetterdaten
    """
    try:
        # Query-Parameter extrahieren
        params: Dict[str, str] = dict(request.query_params)

        if not params:
            log.warning("Keine Query-Parameter empfangen")
            return JSONResponse(
                status_code=400,
                content={"error": "No query parameters"}
            )

        log.debug("Wetterdaten empfangen: %d Parameter", len(params))

        # Device Manager aus app.state holen
        device_manager = request.app.state.device_manager
        db = request.app.state.db

        # Sainlogic-Adapter finden
        devices = device_manager.get_devices_by_type("sainlogic-ws3500")
        if not devices:
            log.error("Kein Sainlogic-Gerät konfiguriert")
            return JSONResponse(
                status_code=500,
                content={"error": "No weather station configured"}
            )

        device = devices[0]  # Erstes Gerät verwenden
        adapter = device.adapter

        # Daten verarbeiten (Ecowitt → WeatherReading)
        reading = adapter.process_ecowitt_data(params)

        if reading is None:
            log.error("Fehler beim Verarbeiten der Wetterdaten")
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to process weather data"}
            )

        # In Datenbank speichern
        try:
            db.insert_weather_reading(reading)
            log.info("Wetterdaten gespeichert: %.1f°C, %d%% Luftfeuchte",
                    reading.temp_c or 0, reading.humidity or 0)
        except Exception as e:
            log.error("Fehler beim Speichern in DB: %s", e)

        # MQTT publizieren
        mqtt_config = device.config.get("mqtt", {})
        base_topic = mqtt_config.get("base_topic", "hc_weda/wetterstation")
        publish_fields = mqtt_config.get("publish_fields", {})

        # Payload erstellen (mit deutschen Feldnamen)
        mqtt_payload = _create_mqtt_payload(reading, publish_fields, device)

        success = mqtt.publish(base_topic, mqtt_payload, retain=True)
        if success:
            log.debug("Wetterdaten via MQTT publiziert")
        else:
            log.warning("MQTT Publish fehlgeschlagen")

        # Webhook an Home Assistant
        try:
            notify_ha(
                "weather_data",
                temp_c=reading.temp_c,
                feels_like_c=reading.feels_like_c,
                humidity=reading.humidity,
                indoor_temp_c=reading.indoor_temp_c,
                indoor_humidity=reading.indoor_humidity,
                temp_diff_c=reading.temp_diff_c,
                climate_advice=reading.climate_advice,
                wind_kmh=reading.wind_speed_kmh,
                wind_gust_kmh=reading.wind_gust_kmh,
                wind_dir=reading.wind_dir_deg,
                wind_dir_text=reading.wind_dir_text,
                beaufort=reading.beaufort,
                beaufort_text=reading.beaufort_text,
                pressure_hpa=reading.pressure_hpa,
                rain_daily_mm=reading.rain_daily_mm,
                rain_monthly_mm=reading.rain_monthly_mm,
                solar_klux=reading.solar_klux,
                uv_index=reading.uv_index,
                dewpoint_c=reading.dewpoint_c,
                frost_text=reading.frost_text,
            )
        except Exception as e:
            log.warning("Webhook fehlgeschlagen: %s", e)

        # Wetter-Warnungen prüfen
        if weather_alerts:
            try:
                weather_alerts.check_alerts(reading)
            except Exception as e:
                log.error("Fehler bei Warnungs-Prüfung: %s", e)

        # HTTP-Antwort (JSON mit verarbeiteten Daten)
        response_data = {
            "status": "ok",
            "timestamp": reading.timestamp,
            "data": {
                "temp_c": reading.temp_c,
                "feels_like_c": reading.feels_like_c,
                "humidity": reading.humidity,
                "wind_kmh": reading.wind_speed_kmh,
                "pressure_hpa": reading.pressure_hpa,
                "rain_daily_mm": reading.rain_daily_mm,
            }
        }

        return JSONResponse(status_code=200, content=response_data)

    except Exception as e:
        log.error("Fehler beim Verarbeiten der Anfrage: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


def _create_mqtt_payload(reading, field_mapping: dict, device) -> dict:
    """Erstellt MQTT-Payload mit deutschen Feldnamen.

    Args:
        reading: WeatherReading
        field_mapping: Dict mit Mapping (interner_name -> mqtt_name)
        device: ManagedDevice

    Returns:
        Dict mit MQTT-Payload
    """
    # Basis-Payload
    payload = {
        "geraete_id": device.device_id,
        "geraete_name": device.device_name,
        "zeitstempel": reading.timestamp,
        "datum": reading.date,
        "uhrzeit": reading.time,
        "quelle": reading.source,
    }

    # Alle Felder aus WeatherReading
    reading_dict = {
        "temp_c": reading.temp_c,
        "temp_f": reading.temp_f,
        "feels_like_c": reading.feels_like_c,
        "indoor_temp_c": reading.indoor_temp_c,
        "dewpoint_c": reading.dewpoint_c,
        "windchill_c": reading.windchill_c,
        "humidity": reading.humidity,
        "indoor_humidity": reading.indoor_humidity,
        "wind_speed_kmh": reading.wind_speed_kmh,
        "wind_speed_mph": reading.wind_speed_mph,
        "wind_gust_kmh": reading.wind_gust_kmh,
        "wind_dir_deg": reading.wind_dir_deg,
        "wind_dir_text": reading.wind_dir_text,
        "beaufort": reading.beaufort,
        "beaufort_text": reading.beaufort_text,
        "rain_rate_mmh": reading.rain_rate_mmh,
        "rain_daily_mm": reading.rain_daily_mm,
        "rain_weekly_mm": reading.rain_weekly_mm,
        "rain_monthly_mm": reading.rain_monthly_mm,
        "pressure_hpa": reading.pressure_hpa,
        "pressure_inhg": reading.pressure_inhg,
        "abs_pressure_hpa": reading.abs_pressure_hpa,
        "solar_radiation": reading.solar_radiation,
        "solar_klux": reading.solar_klux,
        "uv_index": reading.uv_index,
        "temp_diff_c": reading.temp_diff_c,
        "climate_advice": reading.climate_advice,
        "frost_text": reading.frost_text,
    }

    # Mapping anwenden (interner_name -> mqtt_name)
    for internal_name, mqtt_name in field_mapping.items():
        if internal_name in reading_dict:
            value = reading_dict[internal_name]
            if value is not None:  # Nur nicht-None Werte
                payload[mqtt_name] = value

    return payload
