# Changelog - hc_weda v2

## v2.0.0 - 2026-05-09

### ✨ Neue Features
- **Dashboard v2**: Komplett überarbeitetes Dashboard mit Gauge-Kacheln
  - 5 Tabs: Aktuell, Heute, Vorhersage, Verlauf, Statistik
  - Responsive Design (Desktop & Mobile)
  - Dark/Light Theme
  - Auto-Refresh alle 60 Sekunden
  - Wettervorhersage via Open-Meteo API (kostenlos)
  
- **Wetter-Warnungen**: Automatische Webhooks an Home Assistant
  - Sturm-Warnung (Wind > 50 km/h oder Böen > 70 km/h)
  - Starkregen-Warnung (Regen > 10 mm/h)
  - Frost-Warnung (Temp ≤ 0°C)
  - Frostgefahr-Warnung (Temp ≤ 3°C)
  - Hysterese & Cooldown gegen Flapping
  - Konfigurierbare Schwellwerte in .env

- **Zeitzone-Konvertierung**: UTC → Lokalzeit (Europe/Vaduz, UTC+1/+2)
  - Automatische DST-Erkennung (Sommer/Winter)
  - Korrekte Zeitstempel in Dashboard und Datenbank

- **NGINX Reverse Proxy Support**: Dashboard funktioniert mit Subpath
  - Automatische URL-Präfix-Erkennung
  - Relative Pfade für CSS/JS
  - Funktioniert lokal und via NGINX

### 🔧 Verbesserungen
- **Chart-Optimierungen**:
  - X-Achsen-Labels: 45° Rotation, max. 12 Labels
  - Deutsche Lokalisierung (24h-Format)
  - Desktop: Größerer Temperaturverlauf (360px)
  - Mobile: Kompakte Ansicht (260px)
  - Wind-Chart: Grüne Fläche + Orange Linie (statt gestrichelt)

- **FastAPI statt Flask**: Moderne async API
- **Pydantic Models**: Type-safe Datenmodelle
- **Strukturierte Logs**: Besseres Debugging
- **Home Assistant Discovery**: Automatische Sensor-Erkennung
- **Webhooks**: Events für app_start, app_stop, weather_data, weather_alert

### 📦 Migration von v1
- Datenbank: `history.db` → `weather.db` (980k+ Messungen migriert)
- Port-Mapping: 8090 (Dashboard), 8089 (Weather Receiver)
- MQTT Topic: `wetterstation/data` → `hc_weda/*`
- Alle v1-Features erhalten (CSV-Import, HA-Discovery, Webhooks)

### 🐛 Bugfixes
- Zeitstempel-Problem behoben (UTC → Lokalzeit)
- Chart-Labels lesbar gemacht (Rotation + Limit)
- Wind-Chart übersichtlicher (Fläche + Linie)
- NGINX Subpath funktioniert korrekt

### 📚 Dokumentation
- `docs/WEATHER_ALERTS.md`: Warnungs-Dokumentation
- `CHANGELOG.md`: Versionshistorie
- Kommentare in allen Modulen

### ⚙️ Konfiguration
Neue .env-Variablen:
```bash
# Wetter-Warnungen
ALERT_STORM_WIND=50.0
ALERT_STORM_GUST=70.0
ALERT_HEAVY_RAIN=10.0
ALERT_FROST=0.0
ALERT_FREEZE_RISK=3.0
ALERT_MIN_DURATION=15
ALERT_COOLDOWN=5
```

### 🚀 Deployment
```bash
cd /dockerapps/apps_v2/hc_weda
docker-compose down
docker-compose build
docker-compose up -d
```

Dashboard: http://10.1.1.119:8090/
NGINX: https://ips.siebler.at/dashboardwetter/
