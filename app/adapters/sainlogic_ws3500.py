# -*- coding: utf-8 -*-
"""
Sainlogic WS3500 Wetterstation Adapter
======================================
Empfängt HTTP GET Requests von der Wetterstation (Ecowitt-Protokoll).
Konvertiert Fahrenheit → Celsius, Inches → mm, MPH → km/h.
Berechnet abgeleitete Werte (gefühlte Temperatur, Beaufort, etc.).
"""
from datetime import datetime
from typing import Optional

from app.adapters.base import DatasourceAdapter
from app.core.logging import setup_logger
from app.models.weather import DeviceInfo, WeatherReading
from app.adapters.ecowitt_validator import EcowittValidator

log = setup_logger("adapter.sainlogic")


class SainlogicWS3500Adapter(DatasourceAdapter):
    """Adapter für Sainlogic WS3500 Wetterstation (HTTP Receiver)."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.last_reading: Optional[WeatherReading] = None
        self.last_update: Optional[datetime] = None
        self.validator = EcowittValidator()

    def process_ecowitt_data(self, params: dict) -> Optional[WeatherReading]:
        """Verarbeitet Ecowitt-Protokoll Query-Parameter.

        Ecowitt-Format (Beispiel):

          indoortempf=74.8&tempf=49.3&dewptf=41.7&windchillf=48.6
          &indoorhumidity=41&humidity=75&windspeedmph=3.4
          &windgustmph=4.5&winddir=319&absbaromin=28.521
          &baromin=29.637&rainin=0.000&dailyrainin=0.000
          &weeklyrainin=0.000&monthlyrainin=2.150
          &solarradiation=258.98&UV=2
          &dateutc=2026-05-17%2006:26:38
          &softwaretype=EasyWeatherV1.7.3
          &action=updateraw
          &realtime=1&rtfreq=5 HTTP/1.1" 200 OK

        Args:
            params: Dict mit Query-Parametern (lowercase keys)

        Returns:
            WeatherReading oder None bei Fehler
        """
        try:
            # Alle Keys in lowercase umwandeln
            params = {k.lower(): v for k, v in params.items()}

            # -------------------------------------------------
            # VALIDIERUNG
            # -------------------------------------------------
            # Extrahiert und validiert alle relevanten Rohwerte.
            # Gibt None zurück, wenn Daten unbrauchbar sind.
            raw = self.validator.extract_raw(params)
            if raw is None:
                log.error("Fehler beim Verarbeiten der Wetterdaten: Ungültige oder unvollständige Ecowitt-Daten")
                return None

            # Timestamp von Wetterstation (UTC) in lokale Zeit konvertieren
            # Initialisiere now mit aktuellem Zeitpunkt (Fallback)
            now = datetime.now()

            timestamp_utc = params.get("dateutc")
            if timestamp_utc:
                # Ersetze '+' durch ' ' (URL-Encoding)
                timestamp_utc = timestamp_utc.replace("+", " ")
                try:
                    # Parse UTC timestamp
                    dt_utc = datetime.strptime(timestamp_utc, "%Y-%m-%d %H:%M:%S")
                    # Konvertiere zu lokaler Zeit (Europe/Vaduz = UTC+1/+2)
                    from datetime import  timedelta
                    # Sommerzeit-Offset berechnen (vereinfacht: +2h im Sommer, +1h im Winter)
                    import time
                    is_dst = time.localtime().tm_isdst
                    offset_hours = 2 if is_dst else 1
                    dt_local = dt_utc + timedelta(hours=offset_hours)
                    timestamp = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                    now = dt_local  # Für date/time Felder
                    log.debug("UTC → Lokal: %s → %s (Offset: +%dh)", timestamp_utc, timestamp, offset_hours)
                except Exception as e:
                    log.warning("Fehler bei Zeitkonvertierung: %s, verwende UTC", e)
                    timestamp = timestamp_utc
                    # now bleibt datetime.now()
            else:
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            # --- Temperatur (F → C) ---
            temp_f = self._get_float(params, "tempf")
            temp_c = self._f_to_c(temp_f) if temp_f is not None else None

            indoor_temp_f = self._get_float(params, "indoortempf")
            indoor_temp_c = self._f_to_c(indoor_temp_f) if indoor_temp_f is not None else None

            dewpoint_f = self._get_float(params, "dewptf")
            dewpoint_c = self._f_to_c(dewpoint_f) if dewpoint_f is not None else None

            windchill_f = self._get_float(params, "windchillf")
            windchill_c = self._f_to_c(windchill_f) if windchill_f is not None else None

            # --- Luftfeuchte ---
            humidity = self._get_int(params, "humidity")
            indoor_humidity = self._get_int(params, "indoorhumidity")

            # --- Wind (MPH → km/h) ---
            wind_mph = self._get_float(params, "windspeedmph")
            wind_kmh = self._mph_to_kmh(wind_mph) if wind_mph is not None else None

            wind_gust_mph = self._get_float(params, "windgustmph")
            wind_gust_kmh = self._mph_to_kmh(wind_gust_mph) if wind_gust_mph is not None else None

            wind_dir_deg = self._get_int(params, "winddir")
            wind_dir_text = self._wind_direction_text(wind_dir_deg) if wind_dir_deg is not None else None

            # Beaufort-Skala
            beaufort = self._beaufort_scale(wind_kmh) if wind_kmh is not None else None
            beaufort_text = self._beaufort_text(beaufort) if beaufort is not None else None

            # --- Regen (Inches → mm) ---
            rain_rate_in = self._get_float(params, "rainin")
            rain_rate_mm = self._in_to_mm(rain_rate_in) if rain_rate_in is not None else None

            rain_daily_in = self._get_float(params, "dailyrainin")
            rain_daily_mm = self._in_to_mm(rain_daily_in) if rain_daily_in is not None else None

            rain_weekly_in = self._get_float(params, "weeklyrainin")
            rain_weekly_mm = self._in_to_mm(rain_weekly_in) if rain_weekly_in is not None else None

            rain_monthly_in = self._get_float(params, "monthlyrainin")
            rain_monthly_mm = self._in_to_mm(rain_monthly_in) if rain_monthly_in is not None else None

            # --- Luftdruck (InHg → hPa) ---
            pressure_inhg = self._get_float(params, "baromin")
            pressure_hpa = self._inhg_to_hpa(pressure_inhg) if pressure_inhg is not None else None

            abs_pressure_inhg = self._get_float(params, "absbaromin")
            abs_pressure_hpa = self._inhg_to_hpa(abs_pressure_inhg) if abs_pressure_inhg is not None else None

            # --- Solar / UV ---
            solar_radiation = self._get_float(params, "solarradiation")
            solar_klux = self._wm2_to_klux(solar_radiation) if solar_radiation is not None else None
            uv_index = self._get_int(params, "uv")

            # --- Gefühlte Temperatur ---
            feels_like_c = self._calculate_feels_like(
                temp_c, humidity, wind_kmh, solar_radiation
            )

            # --- Raumklima ---
            temp_diff_c = None
            climate_advice = None
            if temp_c is not None and indoor_temp_c is not None:
                temp_diff_c = round(indoor_temp_c - temp_c, 1)
                climate_advice = self._climate_advice(temp_c, indoor_temp_c, humidity, indoor_humidity)

            # --- Frostwarnung ---
            frost_text = self._frost_warning(temp_c) if temp_c is not None else None

            # WeatherReading erstellen
            reading = WeatherReading(
                timestamp=timestamp,
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M:%S"),
                temp_c=temp_c,
                temp_f=temp_f,
                feels_like_c=feels_like_c,
                indoor_temp_c=indoor_temp_c,
                dewpoint_c=dewpoint_c,
                windchill_c=windchill_c,
                humidity=humidity,
                indoor_humidity=indoor_humidity,
                wind_speed_kmh=wind_kmh,
                wind_speed_mph=wind_mph,
                wind_gust_kmh=wind_gust_kmh,
                wind_dir_deg=wind_dir_deg,
                wind_dir_text=wind_dir_text,
                beaufort=beaufort,
                beaufort_text=beaufort_text,
                rain_rate_mmh=rain_rate_mm,
                rain_daily_mm=rain_daily_mm,
                rain_weekly_mm=rain_weekly_mm,
                rain_monthly_mm=rain_monthly_mm,
                pressure_hpa=pressure_hpa,
                pressure_inhg=pressure_inhg,
                abs_pressure_hpa=abs_pressure_hpa,
                solar_radiation=solar_radiation,
                solar_klux=solar_klux,
                uv_index=uv_index,
                temp_diff_c=temp_diff_c,
                climate_advice=climate_advice,
                frost_text=frost_text,
                source="sainlogic-ws3500",
            )

            self.last_reading = reading
            self.last_update = now

            log.debug("Wetterdaten verarbeitet: %.1f°C, %d%% Luftfeuchte",
                     temp_c or 0, humidity or 0)

            return reading

        except Exception as e:
            log.error("Fehler beim Verarbeiten der Wetterdaten: %s", e)
            return None

    def fetch_reading(self) -> Optional[WeatherReading]:
        """Gibt das letzte empfangene Reading zurück.

        Bei HTTP-Receiver wird nicht aktiv gepollt,
        sondern auf eingehende Requests gewartet.
        """
        return self.last_reading

    def fetch_device_info(self) -> Optional[DeviceInfo]:
        """Liefert statische Geräteinformationen aus der Konfiguration."""
        device = self.config.get("device", {})
        return DeviceInfo(
            name=device.get("name", "Wetterstation"),
            device_type="sainlogic-ws3500",
            device_id=device.get("device_id", ""),
            model=device.get("model", "WS3500"),
            manufacturer=device.get("manufacturer", "SAINLOGIC"),
            location=device.get("location", ""),
            latitude=device.get("latitude"),
            longitude=device.get("longitude"),
        )

    def is_reachable(self) -> bool:
        """Prüft ob Wetterstation erreichbar ist (Timeout-Check).

        Returns:
            True wenn letzte Daten < 15 Minuten alt
        """
        if self.last_update is None:
            return False

        timeout = self.config.get("datasource", {}).get("timeout", 900)  # 15 Min
        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed < timeout

    # --- Hilfsfunktionen: Einheiten-Konvertierung ---

    @staticmethod
    def _get_float(params: dict, key: str) -> Optional[float]:
        """Holt Float-Wert aus Dict."""
        try:
            value = params.get(key)
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _get_int(params: dict, key: str) -> Optional[int]:
        """Holt Int-Wert aus Dict."""
        try:
            value = params.get(key)
            return int(float(value)) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _f_to_c(fahrenheit: float) -> float:
        """Fahrenheit → Celsius."""
        return round((fahrenheit - 32) * 5 / 9, 1)

    @staticmethod
    def _mph_to_kmh(mph: float) -> float:
        """MPH → km/h."""
        return round(mph * 1.60934, 1)

    @staticmethod
    def _in_to_mm(inches: float) -> float:
        """Inches → mm."""
        return round(inches * 25.4, 1)

    @staticmethod
    def _inhg_to_hpa(inhg: float) -> float:
        """InHg → hPa."""
        return round(inhg * 33.8639, 1)

    @staticmethod
    def _wm2_to_klux(wm2: float) -> float:
        """W/m² → Klux (Näherung: 1 W/m² ≈ 0.0079 Klux)."""
        return round(wm2 * 0.0079, 2)

    @staticmethod
    def _wind_direction_text(degrees: int) -> str:
        """Windrichtung in Grad → Text (N, NO, O, SO, S, SW, W, NW)."""
        directions = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
        index = round(degrees / 45) % 8
        return directions[index]

    @staticmethod
    def _beaufort_scale(wind_kmh: float) -> int:
        """Windgeschwindigkeit → Beaufort-Skala (0-12)."""
        if wind_kmh < 1:
            return 0
        elif wind_kmh < 6:
            return 1
        elif wind_kmh < 12:
            return 2
        elif wind_kmh < 20:
            return 3
        elif wind_kmh < 29:
            return 4
        elif wind_kmh < 39:
            return 5
        elif wind_kmh < 50:
            return 6
        elif wind_kmh < 62:
            return 7
        elif wind_kmh < 75:
            return 8
        elif wind_kmh < 89:
            return 9
        elif wind_kmh < 103:
            return 10
        elif wind_kmh < 118:
            return 11
        else:
            return 12

    @staticmethod
    def _beaufort_text(beaufort: int) -> str:
        """Beaufort-Skala → Text."""
        texts = [
            "Windstille", "leiser Zug", "leichte Brise", "schwache Brise",
            "mäßige Brise", "frische Brise", "starker Wind", "steifer Wind",
            "stürmischer Wind", "Sturm", "schwerer Sturm", "orkanartiger Sturm", "Orkan"
        ]
        return texts[beaufort] if 0 <= beaufort < len(texts) else "unbekannt"

    @staticmethod
    def _calculate_feels_like(temp_c: Optional[float], humidity: Optional[int],
                              wind_kmh: Optional[float], solar: Optional[float]) -> Optional[float]:
        """Berechnet gefühlte Temperatur (vereinfachte Formel).

        Berücksichtigt:
        - Windchill (bei Kälte + Wind)
        - Hitzeindex (bei Wärme + Luftfeuchte)
        - Solar-Strahlung (bei Sonne)
        """
        if temp_c is None:
            return None

        feels_like = temp_c

        # Windchill (bei < 10°C und Wind > 5 km/h)
        if temp_c < 10 and wind_kmh is not None and wind_kmh > 5:
            windchill = 13.12 + 0.6215 * temp_c - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp_c * (wind_kmh ** 0.16)
            feels_like = min(feels_like, windchill)

        # Hitzeindex (bei > 27°C und Luftfeuchte > 40%)
        if temp_c > 27 and humidity is not None and humidity > 40:
            heat_index = -8.78469475556 + 1.61139411 * temp_c + 2.33854883889 * humidity
            heat_index += -0.14611605 * temp_c * humidity - 0.012308094 * (temp_c ** 2)
            heat_index += -0.0164248277778 * (humidity ** 2) + 0.002211732 * (temp_c ** 2) * humidity
            heat_index += 0.00072546 * temp_c * (humidity ** 2) - 0.000003582 * (temp_c ** 2) * (humidity ** 2)
            feels_like = max(feels_like, heat_index)

        # Solar-Strahlung (bei > 500 W/m²: +2°C)
        if solar is not None and solar > 500:
            feels_like += 2

        return round(feels_like, 1)

    @staticmethod
    def _climate_advice(temp_out: float, temp_in: float,
                       humidity_out: Optional[int], humidity_in: Optional[int]) -> str:
        """Lüftungsempfehlung basierend auf Temperatur und Luftfeuchte."""
        diff = temp_in - temp_out

        if diff > 5:
            return "Lüften empfohlen (Innen wärmer)"
        elif diff < -5:
            return "Fenster schließen (Außen wärmer)"
        elif humidity_in is not None and humidity_in > 65:
            return "Lüften (hohe Luftfeuchte innen)"
        elif humidity_in is not None and humidity_in < 30:
            return "Luftbefeuchter nutzen (trockene Luft)"
        else:
            return "Raumklima optimal"

    @staticmethod
    def _frost_warning(temp_c: float) -> Optional[str]:
        """Frostwarnung bei Temperaturen < 3°C."""
        if temp_c <= 0:
            return "Frost! (≤ 0°C)"
        elif temp_c <= 3:
            return "Frostgefahr (≤ 3°C)"
        return None
