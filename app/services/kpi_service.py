# app/services/kpi_service.py
"""KPI-Service für hc_weda – liefert Wetter-Übersichtsdaten für das zentrale Dashboard."""

from datetime import datetime

from app.core.config import KPI_APP_ID, KPI_APP_NAME, KPI_ICON, KPI_URL
from app.core.logging import setup_logger
from app.schemas.kpi import KpiHero, KpiIndicator, KpiMetric, KpiResponse
from app.services.database import get_db

log = setup_logger("kpi_service")


class KpiService:
    """Aggregiert Wetter-KPI-Daten aus der measurements-Tabelle."""

    def get_kpis(self) -> KpiResponse:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        db = get_db()

        # Aktuellster Messwert
        latest = db.get_latest_reading()

        if not latest:
            return KpiResponse(
                app_id=KPI_APP_ID,
                app_name=KPI_APP_NAME,
                icon=KPI_ICON,
                url=KPI_URL,
                status="error",
                ts=now.isoformat(timespec="seconds"),
                hero=KpiHero(value="–", unit="", label="Keine Daten"),
                detail="",
            )

        # Aktuelle Werte
        temp = latest.get("temp_c")
        feels_like = latest.get("feels_like_c")
        humidity = latest.get("humidity")
        wind_kmh = latest.get("windspeed_kmh") or latest.get("wind_speed_kmh") or 0
        wind_gust = latest.get("wind_gust_kmh") or 0
        wind_dir = latest.get("wind_dir_text") or ""
        rain_daily = latest.get("daily_rain_mm") or latest.get("rain_daily_mm") or 0
        pressure = latest.get("pressure_hpa") or latest.get("abs_pressure_hpa")
        solar = latest.get("solar_radiation")
        solar_klux = latest.get("solar_klux")
        uv_index = latest.get("uv_index")
        indoor_temp = latest.get("indoor_temp_c")

        # Tages-Min/Max aus DB
        summary = db.get_daily_summary(today)
        temp_min = summary.get("temp_min") if summary else None
        temp_max = summary.get("temp_max") if summary else None
        temp_avg = summary.get("temp_avg") if summary else None

        # Status: warning wenn keine Daten seit >15 min
        status = "ok"
        last_ts = latest.get("dateutc", "")
        if last_ts:
            try:
                last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00").replace(" ", "T"))
                age_min = (now - last_dt.replace(tzinfo=None)).total_seconds() / 60
                if age_min > 15:
                    status = "warning"
            except (ValueError, TypeError):
                pass

        # Detail-Zeile
        parts = []
        if temp_min is not None and temp_max is not None:
            parts.append(f"Min {temp_min:.0f}  Max {temp_max:.0f}")
        if temp_avg is not None:
            parts.append(f"⌀ {temp_avg:.0f}")
        detail = "  ".join(parts)

        # Label unter Hero: Gefühlt + weitere Info
        label_parts = []
        if feels_like is not None and temp is not None and abs(feels_like - temp) > 1:
            label_parts.append(f"Gefühlt {feels_like:.1f} °C")
        if humidity is not None:
            label_parts.append(f"Feuchte {humidity} %")
        if wind_kmh > 0:
            label_parts.append(f"Wind {wind_kmh:.0f} km/h")
        label = " · ".join(label_parts)

        # Gauge-Indikator: Temperatur von -20 bis 40
        indicator = KpiIndicator(
            type="gauge",
            min=-20,
            max=40,
            value=temp,
            zones=[
                {"from": -20, "to": 0, "color": "#3b82f6"},
                {"from": 0, "to": 15, "color": "#22c55e"},
                {"from": 15, "to": 30, "color": "#f59e0b"},
                {"from": 30, "to": 40, "color": "#ef4444"},
            ],
        )

        return KpiResponse(
            app_id=KPI_APP_ID,
            app_name=KPI_APP_NAME,
            icon=KPI_ICON,
            url=KPI_URL,
            status=status,
            ts=now.isoformat(timespec="seconds"),
            hero=KpiHero(
                value=round(temp, 1) if temp is not None else "–",
                unit="°C",
                label=label,
            ),
            detail=detail,
            indicator=indicator,
            metrics=[
                m for m in [
                    KpiMetric(label="Gefühlt", value=round(feels_like, 1), unit="°C") if feels_like is not None else None,
                    KpiMetric(label="Feuchte", value=int(humidity), unit="%") if humidity is not None else None,
                    KpiMetric(label="Wind", value=round(wind_kmh, 0), unit="km/h") if wind_kmh > 0 else None,
                    KpiMetric(label="Böen", value=round(wind_gust, 0), unit="km/h") if wind_gust > 0 else None,
                    KpiMetric(label="Richtung", value=wind_dir) if wind_dir else None,
                    KpiMetric(label="Luftdruck", value=round(pressure, 0), unit="hPa") if pressure else None,
                    KpiMetric(label="Regen", value=round(rain_daily, 1), unit="mm") if rain_daily > 0 else None,
                    KpiMetric(label="Solar", value=round(solar_klux, 1), unit="klux") if solar_klux else (
                        KpiMetric(label="Solar", value=round(solar, 0), unit="W/m²") if solar else None),
                    KpiMetric(label="UV", value=uv_index) if uv_index is not None else None,
                    KpiMetric(label="Innen", value=round(indoor_temp, 1), unit="°C") if indoor_temp is not None else None,
                    KpiMetric(label="Min", value=round(temp_min, 1), unit="°C") if temp_min is not None else None,
                    KpiMetric(label="Max", value=round(temp_max, 1), unit="°C") if temp_max is not None else None,
                ] if m is not None
            ] or None,
        )
