# -*- coding: utf-8 -*-
"""Health Check Route."""

from fastapi import APIRouter

from app.core.config import APP_NAME, APP_VERSION

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
    }
