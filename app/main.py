from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.devices import router as devices_router
from app.api.routes.health import router as health_router
from app.api.routes.weather_receiver import init_weather_alerts
from app.api.routes.weather_receiver import router as weather_receiver_router
from app.core import ha_discovery, mqtt
from app.core.config import APP_NAME, APP_VERSION, HA_BASETOPIC, HOST, PORT, HA_DISCOVERY_ON
from app.core.logging import setup_logger
from app.core.webhook import notify_ha
from app.services.database import init_db
from app.services.device_manager import DeviceManager
# from app.services.polling_service import PollingService  # Nicht benötigt für Wetterstation

log = setup_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Events."""
    log.info("%s v%s starting", APP_NAME, APP_VERSION)

    # 1. Datenbank initialisieren
    db = init_db()
    log.info("Datenbank initialisiert")

    # 2. Device Manager laden (liest YAML-Configs)
    device_manager = DeviceManager(db)
    log.info("Device Manager: %d Geräte geladen", len(device_manager.get_all_devices()))

    # 3. CSV-Watcher starten (für alle Geräte) - NICHT BENÖTIGT für Wetterstation
    # device_manager.start_all_watchers()
    # log.info("CSV-Watcher gestartet")

    # 4. Polling-Service starten - NICHT BENÖTIGT für Wetterstation (HTTP Receiver)
    # polling_service = PollingService(device_manager, db)
    # polling_service.start()
    # log.info("Polling-Service gestartet")
    polling_service = None  # Dummy für Kompatibilität

    # 5. App-Status via MQTT publizieren
    _publish_app_status("online", device_manager)

    # 6. Home Assistant Discovery publizieren
    if HA_DISCOVERY_ON:
        _publish_ha_discovery(device_manager)

    # 7. Wetter-Warnsystem initialisieren
    init_weather_alerts()
    log.info("Wetter-Warnsystem initialisiert")

    # 8. Webhook: App gestartet
    notify_ha(
        "app_start",
        devices_count=len(device_manager.get_all_devices()),
        devices=[
            {"id": d.device_id, "name": d.device_name, "type": d.device_type}
            for d in device_manager.get_all_devices()
        ]
    )

    # Services in app.state speichern (für API-Zugriff)
    app.state.device_manager = device_manager
    app.state.polling_service = polling_service
    app.state.db = db

    yield

    # Shutdown
    log.info("%s shutting down", APP_NAME)
    _publish_app_status("offline", device_manager)
    notify_ha("app_stop")
    # if polling_service:
    #     polling_service.stop()
    # if device_manager:
    #     device_manager.stop_all_watchers()
    db.close()


def _publish_ha_discovery(device_manager: DeviceManager):
    """Publiziert Home Assistant MQTT Discovery Messages."""

    # App-Status Sensor
    ha_discovery.publish_app_status_sensor()
    log.info("HA Discovery: App-Status Sensor publiziert")

    # Geräte-Sensoren
    for device in device_manager.get_all_devices():
        mqtt_config = device.config.get("mqtt", {})
        base_topic = mqtt_config.get("base_topic", f"{HA_BASETOPIC}/{device.device_type}")

        success = ha_discovery.publish_device_discovery(
            device_id=device.device_id,
            device_name=device.device_name,
            device_type=device.device_type,
            base_topic=base_topic,
        )

        if success:
            log.info("HA Discovery: %s publiziert", device.device_name)
        else:
            log.warning("HA Discovery: %s fehlgeschlagen", device.device_name)


def _publish_app_status(status: str, device_manager: DeviceManager = None):
    """Publiziert App-Status via MQTT.
    
    Topic: hc_weda/status
    Payload: {
        "app": "hc_weda",
        "version": "1.0.0",
        "status": "online|offline",
        "devices": [...],
        "timestamp": "..."
    }
    """
    from datetime import datetime

    from app.core.config import HA_BASETOPIC

    devices_info = []
    if device_manager:
        for device in device_manager.get_all_devices():
            devices_info.append({
                "id": device.device_id,
                "name": device.device_name,
                "type": device.device_type,
            })

    payload = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": status,
        "devices": devices_info,
        "timestamp": datetime.now().isoformat(),
    }

    topic = f"{HA_BASETOPIC}/status"

    # Beim ersten Start: LWT setzen
    if status == "online":
        import json
        lwt_payload = payload.copy()
        lwt_payload["status"] = "offline"

        # Client mit LWT erstellen
        client = mqtt.get_client(
            client_id=f"{APP_NAME}_status",
            lwt_topic=topic,
            lwt_payload=json.dumps(lwt_payload)
        )

        if client:
            try:
                # Online-Status publizieren
                client.publish(topic, json.dumps(payload), retain=True)
                client.disconnect()
                log.info("App-Status publiziert: %s (mit LWT)", status)
                return
            except Exception as e:
                log.error("App-Status Publish fehlgeschlagen: %s", e)

    # Fallback: Normales Publish
    success = mqtt.publish(topic, payload, retain=True)
    if success:
        log.info("App-Status publiziert: %s", status)
    else:
        log.warning("App-Status konnte nicht publiziert werden (MQTT nicht verfügbar)")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
)


# Middleware für No-Cache Header
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Nur für HTML/JS/CSS Dateien
        if request.url.path.endswith(('.html', '.js', '.css')):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response


app.add_middleware(NoCacheMiddleware)

# Routes
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(devices_router, prefix="/api", tags=["devices"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(weather_receiver_router, tags=["weather"])  # No prefix for /weatherstation

# Static files (Frontend) - MUSS NACH den API-Routes kommen
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
