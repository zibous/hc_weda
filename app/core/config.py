# -*- coding: utf-8 -*-
"""
Zentrale Konfiguration fuer hc_weda
=========================================
Alle Einstellungen aus .env + sinnvolle Defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_NAME = os.getenv("APP_NAME", "hc_weda")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# ----------- Pfade -----------
PATHS = {
    "root": PROJECT_ROOT,
    "config": PROJECT_ROOT / "config",
    "data": PROJECT_ROOT / "data",
    "logs": PROJECT_ROOT / "logs",
}

# ----------- HTTP Server -----------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
APPLICATION_ROOT = os.getenv("APPLICATION_ROOT", "/")

# ----------- Logging -----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_MODE = os.getenv("LOG_MODE", "console")
LOG_FILE = os.getenv("LOG_FILE", "logs/hc_weda.log")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", 1_000_000))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 3))

# ----------- MQTT -----------
MQTT_BROKER = os.getenv("MQTT_BROKER", "10.1.1.119")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")

# ----------- Home Assistant -----------
HA_BASETOPIC = os.getenv("HA_BASETOPIC", "").strip()
HA_DISCOVERY = os.getenv("HA_DISCOVERY", "").strip()
HA_DISCOVERY_ON = bool(HA_DISCOVERY)

# ----------- Webhook -----------
HA_WEBHOOK_URL = os.getenv("HA_WEBHOOK_URL", "")
HA_WEBHOOK_ID = os.getenv("HA_WEBHOOK_ID", "")

# ----------- Database -----------
DB_PATH = os.getenv("DB_PATH", "data/weather.db")

# ----------- Weather Forecast (Open-Meteo) -----------
OPENWEATHER_LAT = float(os.getenv("OPENWEATHER_LAT", "47.1410"))
OPENWEATHER_LON = float(os.getenv("OPENWEATHER_LON", "9.5209"))
OPENWEATHER_UNITS = os.getenv("OPENWEATHER_UNITS", "metric")

# ----------- KPI Dashboard -----------
KPI_APP_ID = os.getenv("KPI_APP_ID", "hc_weda")
KPI_APP_NAME = os.getenv("KPI_APP_NAME", "Wetterstation")
KPI_ICON = os.getenv("KPI_ICON", "thermostat")
KPI_URL = os.getenv("KPI_URL", "http://nuc:5021")
