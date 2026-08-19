# -*- coding: utf-8 -*-
"""Routes: Statistiken (Tages-Aggregate, Monats-Regen)."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Request

from app.services.queries.stats import get_daily_stats, get_monthly_rain

router = APIRouter()


@router.get("/stats")
async def api_stats(request: Request):
    """Tages-Aggregation (aus vorberechneten daily_stats)."""
    date_from = request.query_params.get("from", (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"))
    date_to = request.query_params.get("to", datetime.utcnow().strftime("%Y-%m-%d"))
    return get_daily_stats(request.app.state.db, date_from, date_to)


@router.get("/rain/monthly")
async def api_rain_monthly(request: Request):
    """Monatliche Regensummen."""
    date_from = request.query_params.get("from")
    date_to = request.query_params.get("to")
    return get_monthly_rain(request.app.state.db, date_from, date_to)
