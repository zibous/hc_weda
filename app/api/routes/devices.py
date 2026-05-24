# -*- coding: utf-8 -*-
"""Device API Routes."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/devices")
async def list_devices(request: Request):
    """Liste aller konfigurierten Geräte."""
    device_manager = request.app.state.device_manager
    if not device_manager:
        return {"devices": []}

    devices = []
    for device in device_manager.get_all_devices():
        devices.append({
            "device_id": device.device_id,
            "name": device.device_name,
            "type": device.device_type,
            "poll_interval": device.poll_interval,
            "reachable": device.adapter.is_reachable(),
        })

    return {"devices": devices}


@router.get("/devices/{device_id}")
async def get_device(device_id: str, request: Request):
    """Details zu einem Gerät."""
    device_manager = request.app.state.device_manager
    if not device_manager:
        return {"error": "Device Manager nicht initialisiert"}, 500

    device = device_manager.get_device_by_id(device_id)
    if not device:
        return {"error": f"Gerät nicht gefunden: {device_id}"}, 404

    return {
        "device_id": device.device_id,
        "name": device.device_name,
        "type": device.device_type,
        "poll_interval": device.poll_interval,
        "reachable": device.adapter.is_reachable(),
        "config": device.config,
    }


@router.get("/polling/stats")
async def polling_stats(request: Request):
    """Polling-Statistiken."""
    polling_service = request.app.state.polling_service
    if not polling_service:
        return {"error": "Polling-Service nicht initialisiert"}, 500

    return polling_service.get_stats()
