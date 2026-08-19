# -*- coding: utf-8 -*-
"""
Dashboard API Routes – Zusammenfassung
=======================================
Bündelt alle Dashboard-bezogenen Sub-Router unter einem gemeinsamen Router.

Struktur:
  current.py  – Aktueller Messwert, Tageszusammenfassung
  history.py  – Zeitreihen (heute, Datumsbereich)
  stats.py    – Tages-/Monats-Aggregationen
  admin.py    – DB-Stats, Forecast, Cleanup
"""

from fastapi import APIRouter

from .current import router as current_router
from .history import router as history_router
from .stats import router as stats_router
from .admin import router as admin_router

router = APIRouter()

router.include_router(current_router)
router.include_router(history_router)
router.include_router(stats_router)
router.include_router(admin_router)
