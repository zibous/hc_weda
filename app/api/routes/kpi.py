# app/api/routes/kpi.py
"""KPI-Endpoint für das Übersichts-Dashboard."""

from fastapi import APIRouter

from app.schemas.kpi import KpiResponse
from app.services.kpi_service import KpiService

router = APIRouter()


@router.get("/kpidata", response_model=KpiResponse, response_model_exclude_none=True)
async def get_kpi_data():
    """Liefert KPI-Daten für das zentrale Übersichts-Dashboard."""
    service = KpiService()
    return service.get_kpis()
