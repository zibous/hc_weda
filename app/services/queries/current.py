# -*- coding: utf-8 -*-
"""Queries für aktuelle Daten und Tageszusammenfassung."""

from datetime import datetime


def get_latest(db) -> dict | None:
    """Letzter Messwert."""
    row = db.conn.execute("SELECT * FROM measurements ORDER BY dateutc DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def get_today_summary(db) -> dict:
    """Min/Max/Avg-Zusammenfassung des heutigen Tages."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    row = db.conn.execute("""
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
    """, (f"{today}%",)).fetchone()

    return dict(row) if row else {}


def get_today_trends(db) -> dict:
    """Trend-Berechnung: letzte vs. vorletzte Stunde."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    row = db.conn.execute("""
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
    """, (f"{today}%",)).fetchone()

    return dict(row) if row else {}
