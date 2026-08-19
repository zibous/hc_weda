# -*- coding: utf-8 -*-
"""Routes: Zeitreihen (Heute, Verlauf)."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Request

from app.api.routes._helpers import rows_to_series
from app.services.queries.history import get_today_series, get_range_sampled

router = APIRouter()


@router.get("/today")
async def api_today(request: Request):
    """Alle Messungen des heutigen Tages als Zeitreihen."""
    rows = get_today_series(request.app.state.db)
    return {
        "temp": rows_to_series(rows, "temp_c"),
        "humidity": rows_to_series(rows, "humidity"),
        "pressure": rows_to_series(rows, "pressure_hpa"),
        "wind": rows_to_series(rows, "windspeed_kmh"),
        "gust": rows_to_series(rows, "windgust_kmh"),
        "solar": rows_to_series(rows, "solarradiation"),
        "rain": rows_to_series(rows, "daily_rain_mm"),
        "indoor_temp": rows_to_series(rows, "indoor_temp_c"),
        "indoor_hum": rows_to_series(rows, "indoorhumidity"),
    }


@router.get("/range")
async def api_range(request: Request):
    """Messungen in einem Zeitraum (optimiert mit SQL-Sampling)."""
    date_from = request.query_params.get("from", (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"))
    date_to = request.query_params.get("to", datetime.utcnow().strftime("%Y-%m-%d"))

    rows = get_range_sampled(request.app.state.db, date_from, date_to)
    return {
        "temp": rows_to_series(rows, "temp_c"),
        "humidity": rows_to_series(rows, "humidity"),
        "pressure": rows_to_series(rows, "pressure_hpa"),
        "wind": rows_to_series(rows, "windspeed_kmh"),
        "solar": rows_to_series(rows, "solarradiation"),
        "rain": rows_to_series(rows, "daily_rain_mm"),
    }
