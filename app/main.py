# -*- coding: utf-8 -*-
"""hc_weda — Wetterstation (Sainlogic WS3500)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import APP_NAME, APP_VERSION, HOST, PORT, HA_DISCOVERY_ON
from app.core.logging import setup_logger
from app.core.webhook import notify_ha
from app.services.database import init_db
from app.services.device_manager import DeviceManager
from app.services.startup import publish_app_status, publish_ha_discovery, send_app_start

log = setup_logger("main")


# =================================================================
# LIFESPAN
# =================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("%s v%s starting", APP_NAME, APP_VERSION)

    # 1. Datenbank
    db = init_db()
    log.info("Datenbank initialisiert")

    # 2. Device Manager
    device_manager = DeviceManager(db)
    log.info("Device Manager: %d Geräte", len(device_manager.get_all_devices()))

    # 3. MQTT Status + Discovery
    publish_app_status("online", device_manager)
    if HA_DISCOVERY_ON:
        publish_ha_discovery(device_manager)

    # 4. Wetter-Warnsystem
    from app.api.routes.weather_receiver import init_weather_alerts
    init_weather_alerts()
    log.info("Wetter-Warnsystem initialisiert")

    # 5. Webhook: App gestartet
    send_app_start(device_manager)

    # App State
    app.state.device_manager = device_manager
    app.state.db = db

    log.info("✅ Infrastruktur gestartet")
    yield

    # Shutdown
    log.info("Shutdown...")
    publish_app_status("offline", device_manager)
    notify_ha("app_stop")
    db.close()


# =================================================================
# FastAPI App
# =================================================================
app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.endswith((".html", ".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheMiddleware)

# Routes
from app.api.routes.health import router as health_router
from app.api.routes.devices import router as devices_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.kpi import router as kpi_router
from app.api.routes.weather_receiver import router as weather_receiver_router

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(devices_router, prefix="/api", tags=["devices"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(kpi_router, prefix="/api", tags=["kpi"])
app.include_router(weather_receiver_router, tags=["weather"])

# Frontend
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
