# Dashboard Integration v1 → v2

## Übersicht

Das professionelle Dashboard von hc_weda v1 wurde erfolgreich in v2 integriert.

## Was wurde gemacht

### 1. Frontend-Dateien kopiert

```bash
cp /dockerapps/apps_v1/hc_weda/dashboard/templates/index.html → /dockerapps/apps_v2/hc_weda/frontend/static/
cp /dockerapps/apps_v1/hc_weda/dashboard/static/dashboard.js → /dockerapps/apps_v2/hc_weda/frontend/static/
cp /dockerapps/apps_v1/hc_weda/dashboard/static/dashboard.css → /dockerapps/apps_v2/hc_weda/frontend/static/
```

### 2. HTML-Template angepasst

**Änderungen in `index.html`:**
- Flask-Template-Variablen entfernt (`{{ ... }}`)
- Statische Platzhalter eingefügt (werden via JavaScript befüllt)
- URL-Prefix auf `/static/` geändert (FastAPI-kompatibel)
- Alle Werte werden jetzt dynamisch via API geladen

**Beispiel:**
```html
<!-- Vorher (Flask): -->
<div class="card-value">{{ "%.1f"|format(current.get('tempC', 0)) }}</div>

<!-- Nachher (FastAPI): -->
<div class="card-value" id="c-temp">–<span class="unit">°C</span></div>
```

### 3. API-Endpoints implementiert

**Neue Endpoints in `app/api/routes/dashboard.py`:**

| Endpoint | Beschreibung | v1 Kompatibel |
|----------|--------------|---------------|
| `/api/current` | Aktueller Messwert | ✅ |
| `/api/today` | Zeitreihen für heute | ✅ |
| `/api/range` | Zeitreihen für Datumsbereich | ✅ |
| `/api/stats` | Tages-Statistiken | ✅ |
| `/api/rain/monthly` | Monatliche Regensummen | ✅ |
| `/api/dbstats` | Datenbank-Statistiken | ✅ |
| `/api/today/summary` | Zusammenfassung für heute | ✅ |
| `/api/forecast` | Wettervorhersage | ⚠️ Platzhalter |

**Wichtige Anpassungen:**
- Alle Queries verwenden `measurements` Tabelle (statt `readings`)
- Feldnamen angepasst: `tempC` → `temp_c`, `windSpeedKmh` → `windspeed_kmh`, etc.
- Zeitreihen-Format: `[[timestamp, value], ...]` (Chart.js-kompatibel)
- Trend-Berechnung: Vergleich letzte vs. vorletzte Stunde

### 4. JavaScript angepasst

**Änderungen in `dashboard.js`:**
- Feldnamen-Mapping aktualisiert (v1 → v2 Schema)
- Zusätzliche Felder hinzugefügt:
  - `c-indoor-hum` (Innenfeuchte)
  - `c-abs-pressure` (Absoluter Luftdruck)
  - `c-dewpoint` (Taupunkt)
  - `c-uv-text` (UV-Index Text)
  - `c-rain-week`, `c-rain-month` (Wochenregen, Monatsregen)
  - `c-windchill` (Windchill)
  - `c-frost-text` (Frostwarnung)
  - `c-wind-dir-text` (Windrichtung Text)
  - `c-bft-text` (Beaufort Text)
- Berechnete Werte:
  - UV-Index Text: niedrig/mittel/hoch/sehr hoch
  - Lüftungsempfehlung basierend auf Luftfeuchte
  - Temperatur-Differenz Innen/Außen

## Dashboard-Features

### Tabs

1. **Aktuell** - Live-Werte mit Gauge-Kacheln
   - Außentemperatur (mit Gefühlter Temperatur, Taupunkt)
   - Innentemperatur (mit Feuchte, Klimaberatung)
   - Luftfeuchte (mit Lüftungsempfehlung)
   - Wind (mit Beaufort-Skala)
   - Windrichtung (mit Kompass)
   - Luftdruck (mit Trend)
   - Niederschlag (Tag/Woche/Monat)
   - Solar/UV (mit UV-Index)
   - Gefühlt/Frost (mit Windchill)

2. **Heute** - Tagesverlauf mit Charts
   - Temperatur & Feuchte (Innen/Außen)
   - Wind & Böen
   - Luftdruck
   - Solar
   - Regen

3. **Vorhersage** - Wettervorhersage (Platzhalter)
   - Aktuell nicht implementiert
   - Benötigt Integration mit Wetter-API (OpenWeatherMap, etc.)

4. **Verlauf** - Historische Daten
   - Datumsbereich-Filter (7/30/90/365 Tage)
   - Temperatur, Feuchte, Luftdruck, Wind, Solar

5. **Statistik** - Aggregierte Daten
   - Tages-Min/Max/Avg
   - Monatlicher Regen
   - Tabellarische Übersicht

### Design

- **Dark Theme** (Standard) mit Light Theme Toggle
- **Gauge-Style Kacheln** mit Skalen und Progress-Bars
- **Chart.js** für Zeitreihen-Visualisierung
- **Responsive** Design (Mobile-optimiert)
- **Auto-Refresh** alle 60 Sekunden

## Datenbank-Schema

Das Dashboard verwendet die `measurements` Tabelle mit folgenden Feldern:

**Imperial (Rohdaten):**
- `tempf`, `indoortempf`, `dewptf`, `windchillf`
- `windspeedmph`, `windgustmph`, `winddir`
- `baromin`, `absbaromin`
- `rainin`, `dailyrainin`, `weeklyrainin`, `monthlyrainin`
- `solarradiation`, `uv`

**Metrisch (Berechnet):**
- `temp_c`, `indoor_temp_c`, `dewpoint_c`, `windchill_c`
- `windspeed_kmh`, `windgust_kmh`
- `pressure_hpa`, `abs_pressure_hpa`
- `rain_mm`, `daily_rain_mm`, `weekly_rain_mm`, `monthly_rain_mm`

**Zusätzlich (v2):**
- `feels_like_c` (Gefühlte Temperatur)
- `wind_dir_text` (Windrichtung Text: N, NO, O, SO, S, SW, W, NW)
- `beaufort` (Beaufort-Skala 0-12)
- `beaufort_text` (Beaufort Text: Windstille, leiser Zug, etc.)
- `temp_diff_c` (Temperatur-Differenz Innen/Außen)
- `climate_advice` (Klimaberatung: optimal, lüften, etc.)
- `frost_text` (Frostwarnung)
- `solar_klux` (Solar in Kilolux)

## Testen

### 1. App starten

```bash
cd /dockerapps/apps_v2/hc_weda
make dev
```

### 2. Dashboard öffnen

```
http://10.1.0.119:5045/
```

### 3. API-Endpoints testen

```bash
# Aktueller Wert
curl http://localhost:5045/api/current | jq

# Heute
curl http://localhost:5045/api/today | jq

# Statistiken
curl http://localhost:5045/api/dbstats | jq

# Zusammenfassung
curl http://localhost:5045/api/today/summary | jq
```

## Bekannte Einschränkungen

1. **Vorhersage-Tab** ist nicht implementiert
   - Benötigt Integration mit Wetter-API
   - Platzhalter-Endpoint vorhanden

2. **Einige v1-Felder fehlen**
   - `friendlyName`, `coordinates`, `firmware` (nicht in v2 Schema)
   - Werden durch statische Werte ersetzt

3. **Forecast-Daten**
   - v1 hatte `core/forecast.py` für Wettervorhersage
   - v2 hat dies noch nicht implementiert

## Nächste Schritte

1. ✅ Dashboard-Integration abgeschlossen
2. ⏳ Wettervorhersage-Integration (optional)
3. ⏳ Produktiv-Deployment
4. ⏳ v1 deaktivieren

## Unterschiede v1 vs v2

| Feature | v1 | v2 |
|---------|----|----|
| Framework | Flask | FastAPI |
| Template Engine | Jinja2 | Statisches HTML + JavaScript |
| Port | 8090 | 5045 (intern), 5021 (extern) |
| Datenbank | `history.db` | `weather.db` |
| Tabelle | `measurements` | `measurements` |
| Forecast | ✅ | ❌ (Platzhalter) |
| MQTT Topic | `wetterstation/data` | `hc_weda/*` |
| Webhook ID | `wetterstation` | `hc_weda` |

## Dateien

```
/dockerapps/apps_v2/hc_weda/
├── frontend/
│   └── static/
│       ├── index.html          # Dashboard HTML (angepasst)
│       ├── dashboard.js        # Dashboard JavaScript (angepasst)
│       └── dashboard.css       # Dashboard CSS (unverändert)
├── app/
│   └── api/
│       └── routes/
│           └── dashboard.py    # API-Endpoints (neu implementiert)
└── DASHBOARD_INTEGRATION.md    # Diese Datei
```

## Autor

Integration durchgeführt am 2026-05-09
