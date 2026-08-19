# -*- coding: utf-8 -*-
"""Queries für Statistiken (Tages-Aggregate, Monats-Regen)."""

from datetime import datetime


def get_daily_stats(db, date_from: str, date_to: str) -> list[dict]:
    """Tagesstatistiken: cached aus daily_stats + heute live."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Vorberechnete Tage aus Cache
    cached_rows = db.conn.execute(
        "SELECT * FROM daily_stats WHERE day BETWEEN ? AND ? AND day < ? ORDER BY day ASC",
        (date_from, date_to, today)
    ).fetchall()
    results = [dict(r) for r in cached_rows]

    # Heutigen Tag live berechnen
    if date_to >= today:
        live_rows = db.conn.execute("""
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
        """, (f"{today} 00:00:00", f"{date_to} 23:59:59")).fetchall()
        results.extend(dict(r) for r in live_rows)

    return results


def get_monthly_rain(db, date_from: str | None, date_to: str | None) -> list[dict]:
    """Monatliche Regensummen aus daily_stats."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if date_from and date_to:
        rows = db.conn.execute("""
            SELECT substr(day, 1, 7) AS month, ROUND(SUM(rain_day), 1) AS rain_total
            FROM daily_stats
            WHERE day BETWEEN ? AND ? AND day < ?
            GROUP BY month
        """, (date_from, date_to, today)).fetchall()
        results = {r["month"]: r["rain_total"] or 0.0 for r in rows}

        # Heutigen Tag live dazurechnen
        if date_to >= today:
            live = db.conn.execute(
                "SELECT ROUND(MAX(daily_rain_mm), 2) AS rain_day FROM measurements WHERE dateutc BETWEEN ? AND ?",
                (f"{today} 00:00:00", f"{today} 23:59:59")
            ).fetchone()
            if live and live["rain_day"]:
                month_key = today[:7]
                results[month_key] = round((results.get(month_key, 0.0) or 0.0) + (live["rain_day"] or 0.0), 1)

        return [{"month": m, "rain_total": results[m]} for m in sorted(results.keys(), reverse=True)]
    else:
        rows = db.conn.execute("""
            SELECT substr(day, 1, 7) AS month, ROUND(SUM(rain_day), 1) AS rain_total
            FROM daily_stats
            GROUP BY month
            ORDER BY month DESC
            LIMIT 13
        """).fetchall()
        return [dict(r) for r in rows]


def get_db_stats(db) -> dict:
    """Datenbank-Statistiken (Anzahl, Zeitraum)."""
    row = db.conn.execute("""
        SELECT COUNT(*) AS total, MIN(dateutc) AS oldest, MAX(dateutc) AS newest
        FROM measurements
    """).fetchone()
    return dict(row) if row else {}
