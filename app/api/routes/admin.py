# -*- coding: utf-8 -*-
"""Routes: Admin (DB-Stats, Forecast, Cleanup)."""

from fastapi import APIRouter, Query, Request

from app.services.queries.stats import get_db_stats

router = APIRouter()


@router.get("/dbstats")
async def api_dbstats(request: Request):
    """Datenbank-Statistiken."""
    return get_db_stats(request.app.state.db)


@router.get("/forecast")
async def api_forecast(
    request: Request,
    hours: int = Query(48, description="Anzahl Stunden")
):
    """Wettervorhersage von Open-Meteo."""
    from app.services.forecast import fetch_forecast
    from app.core.config import OPENWEATHER_LAT, OPENWEATHER_LON

    try:
        return fetch_forecast(latitude=OPENWEATHER_LAT, longitude=OPENWEATHER_LON, hours=hours)
    except Exception as e:
        return {"current": {}, "hourly": [], "error": str(e)}


@router.post("/cleanup")
async def api_cleanup(request: Request):
    """Manueller Cleanup: Archiviert alte Daten."""
    from app.services.cleanup import run_cleanup
    return run_cleanup(request.app.state.db)
