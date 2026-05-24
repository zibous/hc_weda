# -*- coding: utf-8 -*-
"""
Dashboard API Routes
====================
API-Endpoints für das Wetter-Dashboard (kompatibel mit v1).

Endpoints:
  GET /api/current         - Aktueller Messwert
  GET /api/today           - Zeitreihen für heute
  GET /api/range           - Zeitreihen für Datumsbereich
  GET /api/stats           - Tages-Statistiken
  GET /api/rain/monthly    - Monatliche Regensummen
  GET /api/dbstats         - Datenbank-Statistiken
  GET /api/today/summary   - Zusammenfassung für heute
  GET /api/forecast        - Wettervorhersage (Platzhalter)
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Request

router = APIRouter()


def _rows_to_series(rows: list[dict], key: str) -> list:
    """Extrahiert eine Zeitreihe [timestamp, value] aus DB-Rows."""
    result = []
    for r in rows:
        ts = r.get("dateutc", "")
        val = r.get(key)
        if val is not None:
            result.append([ts, val])
    return result


def _calc_trend(recent, prev) -> str:
    """Berechnet Trend-Pfeil: ↑ steigend, ↓ fallend, → stabil."""
    if recent is None or prev is None:
        return "→"
    diff = recent - prev
    if diff > 0.3:
        return "↑"
    elif diff < -0.3:
        return "↓"
    return "→"


@router.get("/current")
async def api_current(request: Request):
    """Aktueller Messwert."""
    db = request.app.state.db
    row = db.conn.execute("SELECT * FROM measurements ORDER BY dateutc DESC LIMIT 1").fetchone()
    if not row:
        return {"error": "Keine Daten"}
    return dict(row)


@router.get("/today")
async def api_today(request: Request):
    """Alle Messungen des heutigen Tages als Zeitreihen."""
    db = request.app.state.db
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    rows = db.conn.execute(
        "SELECT * FROM measurements WHERE dateutc LIKE ? ORDER BY dateutc ASC",
        (f"{today}%",)
    ).fetchall()
    
    rows_dict = [dict(r) for r in rows]
    
    return {
        "temp": _rows_to_series(rows_dict, "temp_c"),
        "humidity": _rows_to_series(rows_dict, "humidity"),
        "pressure": _rows_to_series(rows_dict, "pressure_hpa"),
        "wind": _rows_to_series(rows_dict, "windspeed_kmh"),
        "gust": _rows_to_series(rows_dict, "windgust_kmh"),
        "solar": _rows_to_series(rows_dict, "solarradiation"),
        "rain": _rows_to_series(rows_dict, "daily_rain_mm"),
        "indoor_temp": _rows_to_series(rows_dict, "indoor_temp_c"),
        "indoor_hum": _rows_to_series(rows_dict, "indoorhumidity"),
    }


@router.get("/range")
async def api_range(request: Request):
    """Messungen zwischen zwei Timestamps."""
    db = request.app.state.db
    
    # FastAPI Query-Parameter mit "from" und "to"
    date_from = request.query_params.get("from", (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"))
    date_to = request.query_params.get("to", datetime.utcnow().strftime("%Y-%m-%d"))
    
    rows = db.conn.execute(
        "SELECT * FROM measurements WHERE dateutc BETWEEN ? AND ? ORDER BY dateutc ASC",
        (f"{date_from} 00:00:00", f"{date_to} 23:59:59")
    ).fetchall()
    
    rows_dict = [dict(r) for r in rows]
    
    # Downsampling wenn zu viele Datenpunkte
    if len(rows_dict) > 2000:
        step = max(1, len(rows_dict) // 1000)
        rows_dict = rows_dict[::step]
    
    return {
        "temp": _rows_to_series(rows_dict, "temp_c"),
        "humidity": _rows_to_series(rows_dict, "humidity"),
        "pressure": _rows_to_series(rows_dict, "pressure_hpa"),
        "wind": _rows_to_series(rows_dict, "windspeed_kmh"),
        "solar": _rows_to_series(rows_dict, "solarradiation"),
        "rain": _rows_to_series(rows_dict, "daily_rain_mm"),
    }


@router.get("/stats")
async def api_stats(request: Request):
    """Tages-Aggregation: Min/Max/Avg Temperatur, Regen-Summe, Max Wind."""
    db = request.app.state.db
    
    date_from = request.query_params.get("from", (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"))
    date_to = request.query_params.get("to", datetime.utcnow().strftime("%Y-%m-%d"))
    
    sql = """
    SELECT
        substr(dateutc, 1, 10)  AS day,
        ROUND(MIN(temp_c), 1)   AS temp_min,
        ROUND(MAX(temp_c), 1)   AS temp_max,
        ROUND(AVG(temp_c), 1)   AS temp_avg,
        ROUND(MIN(humidity), 0) AS hum_min,
        ROUND(MAX(humidity), 0) AS hum_max,
        ROUND(AVG(humidity), 0) AS hum_avg,
        ROUND(MAX(windspeed_kmh), 1)  AS wind_max,
        ROUND(MAX(windgust_kmh), 1)   AS gust_max,
        ROUND(MAX(daily_rain_mm), 2)  AS rain_day,
        ROUND(MIN(pressure_hpa), 1)   AS pressure_min,
        ROUND(MAX(pressure_hpa), 1)   AS pressure_max,
        ROUND(MAX(solarradiation), 1) AS solar_max,
        ROUND(MAX(uv), 0)             AS uv_max
    FROM measurements
    WHERE dateutc BETWEEN ? AND ?
      AND temp_c IS NOT NULL
    GROUP BY day
    ORDER BY day ASC
    """
    
    rows = db.conn.execute(sql, (f"{date_from} 00:00:00", f"{date_to} 23:59:59")).fetchall()
    return [dict(r) for r in rows]


@router.get("/rain/monthly")
async def api_rain_monthly(request: Request):
    """Monatlicher Regensum (letzten 13 Monate)."""
    db = request.app.state.db
    
    sql = """
    SELECT
        substr(dateutc, 1, 7) AS month,
        ROUND(MAX(monthly_rain_mm), 1) AS rain_total
    FROM measurements
    WHERE monthly_rain_mm IS NOT NULL
    GROUP BY month
    ORDER BY month DESC
    LIMIT 13
    """
    
    rows = db.conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


@router.get("/dbstats")
async def api_dbstats(request: Request):
    """Statistik über die DB (Anzahl Zeilen, ältester/neuester Eintrag)."""
    db = request.app.state.db
    
    row = db.conn.execute(
        """
        SELECT
            COUNT(*)    AS total,
            MIN(dateutc) AS oldest,
            MAX(dateutc) AS newest
        FROM measurements
        """
    ).fetchone()
    
    return dict(row) if row else {}


@router.get("/today/summary")
async def api_today_summary(request: Request):
    """Zusammenfassung für heute: Min, Max, Avg, Trend für alle wichtigen Werte."""
    db = request.app.state.db
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    sql = """
    SELECT
        ROUND(MIN(temp_c), 1)          AS temp_min,
        ROUND(MAX(temp_c), 1)          AS temp_max,
        ROUND(AVG(temp_c), 1)          AS temp_avg,
        ROUND(MIN(indoor_temp_c), 1)   AS indoor_temp_min,
        ROUND(MAX(indoor_temp_c), 1)   AS indoor_temp_max,
        ROUND(AVG(indoor_temp_c), 1)   AS indoor_temp_avg,
        ROUND(MIN(humidity), 0)        AS hum_min,
        ROUND(MAX(humidity), 0)        AS hum_max,
        ROUND(AVG(humidity), 0)        AS hum_avg,
        ROUND(MAX(windspeed_kmh), 1)   AS wind_max,
        ROUND(AVG(windspeed_kmh), 1)   AS wind_avg,
        ROUND(MAX(windgust_kmh), 1)    AS gust_max,
        ROUND(MIN(pressure_hpa), 1)    AS pressure_min,
        ROUND(MAX(pressure_hpa), 1)    AS pressure_max,
        ROUND(AVG(pressure_hpa), 1)    AS pressure_avg,
        ROUND(MAX(daily_rain_mm), 2)   AS rain_total,
        ROUND(MAX(solarradiation), 1)  AS solar_max,
        ROUND(AVG(solarradiation), 1)  AS solar_avg,
        ROUND(MAX(uv), 0)             AS uv_max,
        COUNT(*)                       AS count
    FROM measurements
    WHERE dateutc LIKE ?
      AND temp_c IS NOT NULL
    """
    
    row = db.conn.execute(sql, (f"{today}%",)).fetchone()
    result = dict(row) if row else {}
    
    # Trend berechnen: Vergleich letzte Stunde vs. vorletzte Stunde
    trend_sql = """
    SELECT
        ROUND(AVG(CASE WHEN dateutc >= datetime('now', '-1 hour') THEN temp_c END), 1) AS temp_recent,
        ROUND(AVG(CASE WHEN dateutc < datetime('now', '-1 hour')
                        AND dateutc >= datetime('now', '-2 hours') THEN temp_c END), 1) AS temp_prev,
        ROUND(AVG(CASE WHEN dateutc >= datetime('now', '-1 hour') THEN pressure_hpa END), 1) AS pressure_recent,
        ROUND(AVG(CASE WHEN dateutc < datetime('now', '-1 hour')
                        AND dateutc >= datetime('now', '-2 hours') THEN pressure_hpa END), 1) AS pressure_prev,
        ROUND(AVG(CASE WHEN dateutc >= datetime('now', '-1 hour') THEN humidity END), 0) AS hum_recent,
        ROUND(AVG(CASE WHEN dateutc < datetime('now', '-1 hour')
                        AND dateutc >= datetime('now', '-2 hours') THEN humidity END), 0) AS hum_prev
    FROM measurements
    WHERE dateutc LIKE ?
    """
    
    trend_row = db.conn.execute(trend_sql, (f"{today}%",)).fetchone()
    if trend_row:
        tr = dict(trend_row)
        result["temp_trend"] = _calc_trend(tr.get("temp_recent"), tr.get("temp_prev"))
        result["pressure_trend"] = _calc_trend(tr.get("pressure_recent"), tr.get("pressure_prev"))
        result["hum_trend"] = _calc_trend(tr.get("hum_recent"), tr.get("hum_prev"))
    
    return result


@router.get("/forecast")
async def api_forecast(
    request: Request,
    hours: int = Query(48, description="Anzahl Stunden")
):
    """Wettervorhersage von Open-Meteo (kostenlos, kein API-Key nötig)."""
    from app.services.forecast import fetch_forecast
    
    # Koordinaten aus Config oder Default (Vaduz)
    from app.core.config import OPENWEATHER_LAT, OPENWEATHER_LON
    
    try:
        forecast_data = fetch_forecast(
            latitude=OPENWEATHER_LAT,
            longitude=OPENWEATHER_LON,
            hours=hours
        )
        return forecast_data
    except Exception as e:
        return {
            "current": {},
            "hourly": [],
            "error": str(e)
        }

