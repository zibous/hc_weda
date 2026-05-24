# -*- coding: utf-8 -*-
"""
Dashboard – Flask-App für Wetterstation-Visualisierung.
Läuft im gleichen Prozess wie app.py auf einem separaten Port.

NGINX-Proxy-Lösung:
  Wenn DASHBOARD_URL_PREFIX gesetzt ist (z.B. "/dashboardwetter"),
  werden ALLE Routen (HTML, API, Static) unter diesem Prefix registriert.
  Flask bedient dann sowohl / als auch /dashboardwetter/.

  NGINX-Konfig:
    location /dashboardwetter/ {
        proxy_pass http://10.1.1.119:8090/dashboardwetter/;
        ...
    }
"""

import json
import threading
from datetime import datetime, timedelta
from flask import Flask, Blueprint, render_template, jsonify, request
from core.history import (
    query_today, query_range,
    query_daily_stats, query_monthly_rain, query_db_stats,
    query_today_summary,
)
from core.logger import setup_logger
from config.settings import DEVICECONFIG, APPLICATION, DASHBOARD_URL_PREFIX

logger = setup_logger("dashboard")

# ---------------------------------------------------------
# Prefix bestimmen
# ---------------------------------------------------------
_prefix = DASHBOARD_URL_PREFIX.strip().rstrip("/") if DASHBOARD_URL_PREFIX else ""

# ---------------------------------------------------------
# Flask-App erstellen – static_folder=None, wir bedienen Static über Blueprint
# ---------------------------------------------------------
dashboard_app = Flask(
    __name__,
    template_folder="templates",
    static_folder=None,       # kein globaler Static-Handler
)
dashboard_app.config["JSON_SORT_KEYS"] = False


# ---------------------------------------------------------
# Blueprint mit allen Routen – wird unter "/" UND unter prefix registriert
# ---------------------------------------------------------
bp = Blueprint(
    "dashboard",
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates",
)


@bp.context_processor
def inject_prefix():
    """Stellt url_prefix in allen Templates zur Verfügung.
    Erkennt automatisch ob der Request über den Prefix-Pfad kam.
    """
    # Wenn der Request-Pfad mit dem Prefix beginnt, Prefix verwenden
    if _prefix and request.path.startswith(_prefix):
        return {"url_prefix": _prefix}
    return {"url_prefix": ""}


# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------

def _load_current() -> dict:
    """Lädt aktuellen Payload aus data/payload.json."""
    try:
        with open("data/payload.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _rows_to_series(rows: list[dict], key: str) -> list:
    """Extrahiert eine Zeitreihe [timestamp, value] aus DB-Rows."""
    result = []
    for r in rows:
        ts = r.get("dateutc", "")
        val = r.get(key)
        if val is not None:
            result.append([ts, val])
    return result


# ---------------------------------------------------------
# Routen (auf dem Blueprint)
# ---------------------------------------------------------

@bp.route("/")
def index():
    current = _load_current()
    stats = query_db_stats()
    return render_template("index.html",
        current=current,
        stats=stats,
        device=DEVICECONFIG,
        app=APPLICATION,
    )


@bp.route("/api/current")
def api_current():
    return jsonify(_load_current())


@bp.route("/api/today")
def api_today():
    rows = query_today()
    return jsonify({
        "temp":     _rows_to_series(rows, "temp_c"),
        "humidity": _rows_to_series(rows, "humidity"),
        "pressure": _rows_to_series(rows, "pressure_hpa"),
        "wind":     _rows_to_series(rows, "windspeed_kmh"),
        "gust":     _rows_to_series(rows, "windgust_kmh"),
        "solar":    _rows_to_series(rows, "solarradiation"),
        "rain":     _rows_to_series(rows, "daily_rain_mm"),
        "indoor_temp": _rows_to_series(rows, "indoor_temp_c"),
        "indoor_hum":  _rows_to_series(rows, "indoorhumidity"),
    })


@bp.route("/api/range")
def api_range():
    date_from = request.args.get("from", (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"))
    date_to   = request.args.get("to",   datetime.utcnow().strftime("%Y-%m-%d"))
    rows = query_range(f"{date_from} 00:00:00", f"{date_to} 23:59:59")
    if len(rows) > 2000:
        rows = rows[::max(1, len(rows) // 1000)]
    return jsonify({
        "temp":     _rows_to_series(rows, "temp_c"),
        "humidity": _rows_to_series(rows, "humidity"),
        "pressure": _rows_to_series(rows, "pressure_hpa"),
        "wind":     _rows_to_series(rows, "windspeed_kmh"),
        "solar":    _rows_to_series(rows, "solarradiation"),
        "rain":     _rows_to_series(rows, "daily_rain_mm"),
    })


@bp.route("/api/stats")
def api_stats():
    date_from = request.args.get("from", (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"))
    date_to   = request.args.get("to",   datetime.utcnow().strftime("%Y-%m-%d"))
    rows = query_daily_stats(f"{date_from} 00:00:00", f"{date_to} 23:59:59")
    return jsonify(rows)


@bp.route("/api/rain/monthly")
def api_rain_monthly():
    return jsonify(query_monthly_rain())


@bp.route("/api/dbstats")
def api_dbstats():
    return jsonify(query_db_stats())


@bp.route("/api/today/summary")
def api_today_summary():
    return jsonify(query_today_summary())


@bp.route("/api/forecast")
def api_forecast():
    from core.forecast import fetch_forecast
    hours = request.args.get("hours", 48, type=int)
    return jsonify(fetch_forecast(hours=hours))


# ---------------------------------------------------------
# Blueprint registrieren: immer unter "/" und optional unter prefix
# ---------------------------------------------------------
dashboard_app.register_blueprint(bp, url_prefix="/")
if _prefix:
    dashboard_app.register_blueprint(bp, url_prefix=_prefix, name="dashboard_prefixed")


# ---------------------------------------------------------
# Server starten (in eigenem Thread)
# ---------------------------------------------------------

def run_dashboard(port: int = 8090) -> None:
    logger.info("Dashboard läuft auf Port %d (prefix=%s)", port, _prefix or "/")
    dashboard_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def start_dashboard_thread(port: int = 8090) -> threading.Thread:
    t = threading.Thread(target=run_dashboard, args=(port,), daemon=True, name="dashboard")
    t.start()
    return t
