# -*- coding: utf-8 -*-
"""Queries für Zeitreihen (Heute, Verlauf)."""

from datetime import datetime


def get_today_series(db) -> list[dict]:
    """Alle Messungen des heutigen Tages."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    rows = db.conn.execute(
        "SELECT * FROM measurements WHERE dateutc LIKE ? ORDER BY dateutc ASC",
        (f"{today}%",)
    ).fetchall()
    return [dict(r) for r in rows]


def get_range_sampled(db, date_from: str, date_to: str, max_points: int = 1000) -> list[dict]:
    """Messungen in einem Zeitraum mit SQL-Sampling bei großen Datenmengen."""
    ts_from = f"{date_from} 00:00:00"
    ts_to = f"{date_to} 23:59:59"

    # Anzahl Datenpunkte ermitteln
    count_row = db.conn.execute(
        "SELECT COUNT(*) AS cnt FROM measurements WHERE dateutc BETWEEN ? AND ?",
        (ts_from, ts_to)
    ).fetchone()
    total = count_row["cnt"] if count_row else 0

    cols = "dateutc, temp_c, humidity, pressure_hpa, windspeed_kmh, solarradiation, daily_rain_mm"

    if total > max_points:
        step = total // max_points
        sql = f"""
        SELECT {cols}
        FROM (
            SELECT *, ROW_NUMBER() OVER (ORDER BY dateutc) AS rn
            FROM measurements
            WHERE dateutc BETWEEN ? AND ?
        )
        WHERE rn % {step} = 0
        ORDER BY dateutc ASC
        """
        rows = db.conn.execute(sql, (ts_from, ts_to)).fetchall()
    else:
        rows = db.conn.execute(
            f"SELECT {cols} FROM measurements WHERE dateutc BETWEEN ? AND ? ORDER BY dateutc ASC",
            (ts_from, ts_to)
        ).fetchall()

    return [dict(r) for r in rows]
