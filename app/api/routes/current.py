# -*- coding: utf-8 -*-
"""Routes: Aktueller Messwert + Tageszusammenfassung."""

from fastapi import APIRouter, Request

from app.api.routes._helpers import calc_trend
from app.services.queries.current import get_latest, get_today_summary, get_today_trends

router = APIRouter()


@router.get("/current")
async def api_current(request: Request):
    """Aktueller Messwert."""
    data = get_latest(request.app.state.db)
    return data or {"error": "Keine Daten"}


@router.get("/today/summary")
async def api_today_summary(request: Request):
    """Zusammenfassung für heute mit Trends."""
    db = request.app.state.db
    result = get_today_summary(db)
    trends = get_today_trends(db)

    if trends:
        result["temp_trend"] = calc_trend(trends.get("temp_recent"), trends.get("temp_prev"))
        result["pressure_trend"] = calc_trend(trends.get("pressure_recent"), trends.get("pressure_prev"))
        result["hum_trend"] = calc_trend(trends.get("hum_recent"), trends.get("hum_prev"))

    return result
