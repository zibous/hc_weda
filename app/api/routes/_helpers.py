# -*- coding: utf-8 -*-
"""Gemeinsame Hilfsfunktionen für Dashboard-API-Routes."""


def rows_to_series(rows: list[dict], key: str) -> list:
    """Extrahiert eine Zeitreihe [timestamp, value] aus DB-Rows."""
    result = []
    for r in rows:
        ts = r.get("dateutc", "")
        val = r.get(key)
        if val is not None:
            result.append([ts, val])
    return result


def calc_trend(recent, prev) -> str:
    """Berechnet Trend-Pfeil: ↑ steigend, ↓ fallend, → stabil."""
    if recent is None or prev is None:
        return "→"
    diff = recent - prev
    if diff > 0.3:
        return "↑"
    elif diff < -0.3:
        return "↓"
    return "→"
