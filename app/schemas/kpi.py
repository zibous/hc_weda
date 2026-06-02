# app/schemas/kpi.py
"""Einheitliches KPI-Schema für das Übersichts-Dashboard.

Dieses Schema ist identisch für alle Apps (hc_waga, hc_smet, hc_bca, etc.).
Jede App liefert unter GET /api/kpidata eine KpiResponse aus.
"""

from typing import Any
from pydantic import BaseModel


class KpiIndicator(BaseModel):
    """Visueller Indikator für die KPI-Karte."""

    type: str  # "gauge" | "sparkline" | "segments" | "trend" | "none"
    min: float | None = None
    max: float | None = None
    value: float | None = None
    values: list[float] | None = None  # für sparkline
    zones: list[dict[str, Any]] | None = None  # für gauge/segments
    trend_pct: float | None = None  # für trend


class KpiHero(BaseModel):
    """Haupt-KPI-Wert (groß dargestellt)."""

    value: float | int | str
    unit: str = ""
    label: str = ""  # Kontext-Zeile unter Hero-Wert


class KpiResponse(BaseModel):
    """Vollständige KPI-Antwort einer App für das Übersichts-Dashboard."""

    app_id: str
    app_name: str
    icon: str = ""
    url: str = ""  # Link zur App-Detail-Seite
    status: str = "ok"  # "ok" | "warning" | "error"
    ts: str
    hero: KpiHero
    detail: str = ""  # Zweite Info-Zeile (Min/Max/Avg etc.)
    indicator: KpiIndicator | None = None
