# hc_weda v2

Wetterstation-Integration für **Sainlogic WS3500** (Ecowitt-Protokoll).

## Features

- 🌡️ **HTTP Receiver** für Wetterstation (Ecowitt-Protokoll)
- 📊 **SQLite Database** mit ~1 Million historischen Messungen (seit April 2024)
- 🔄 **MQTT Integration** mit deutschen Feldnamen
- 🏠 **Home Assistant Discovery** + Webhooks
- 📈 **Web Dashboard** (v1 Dashboard wird weiterverwendet)
- 🔧 **Einheiten-Konvertierung** (Fahrenheit → Celsius, Inches → mm, MPH → km/h)
- 🧮 **Berechnete Werte** (gefühlte Temperatur, Beaufort, Taupunkt, Lüftungsempfehlung)

## Wetterstation

- **Modell**: Sainlogic WS3500 (SAINLOGIC HIGH TECH INNOVATION CO., LIMITED)
- **Protokoll**: Ecowitt (HTTP GET mit Query-Parametern)
- **Standort**: Garten (47.4594353, 9.6361833)
- **Sendeintervall**: 60 Sekunden
- **Empfangsport**: 8089 (HTTP Receiver)

## Migration von v1

**WICHTIG**: Vor dem ersten Start v1 Daten migrieren!

```bash
# 1. v1 Backup erstellen
make backup-v1

# 2. Migration ausführen
make migrate

# 3. Migration prüfen
make migrate-check
```

Details: siehe [MIGRATION.md](MIGRATION.md)

## Quick Start

### Lokal (Development)

```bash
# Shared venv aktivieren
source ../.venv/bin/activate

# Dependencies installieren
make install

# Lokal starten (mit auto-reload)
make dev

# In anderem Terminal: Test-Daten senden
make test-receiver
```

### Docker (Production)

```bash
# Image bauen
make build

# Container starten
make up

# Logs anzeigen
make logs

# Status prüfen
make status-app
```

## Ports

| Port | Beschreibung |
|------|-------------|
| **5021** | Dashboard (extern) |
| **5045** | Dashboard (intern im Container) |
| **8089** | Weather Receiver (Wetterstation → App) |

## API Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/health` | GET | Health Check |
| `/api/devices` | GET | Geräte-Status |
| `/weatherstation` | GET/POST | Weather Receiver (Ecowitt) |
| `/` | GET | Dashboard |

## Wetterdaten-Empfang

Die Wetterstation sendet alle 60 Sekunden Daten an:

```
http://<server-ip>:8089/weatherstation?tempf=68.5&humidity=65&...
```

Die App:
1. Empfängt die Daten (Ecowitt-Format)
2. Konvertiert Einheiten (Imperial → Metrisch)
3. Berechnet abgeleitete Werte (gefühlte Temp, Beaufort, etc.)
4. Speichert in SQLite
5. Publiziert via MQTT
6. Sendet Webhook an Home Assistant

## MQTT Topics

```
hc_weda/wetterstation/
  ├─ geraete_id
  ├─ geraete_name
  ├─ zeitstempel
  ├─ aussentemperatur_c
  ├─ gefuehlte_temperatur_c
  ├─ luftfeuchte_prozent
  ├─ windgeschwindigkeit_kmh
  ├─ windrichtung_text
  ├─ beaufort_skala
  ├─ luftdruck_hpa
  ├─ regen_tag_mm
  ├─ solarstrahlung_klux
  ├─ uv_index
  └─ ...
```

## Datenbank

- **Datei**: `data/weather.db`
- **Tabelle**: `measurements` (kompatibel mit v1)
- **Primärschlüssel**: `dateutc` (Zeitstempel)
- **Felder**: Imperial (Rohdaten) + Metrisch (berechnet) + v2 Zusatzfelder

### Statistiken anzeigen

```bash
make db-stats      # Anzahl, Zeitraum, Größe
make db-latest     # Letzter Messwert
make db-check      # Integrität prüfen
```

## Makefile Commands

### Development
```bash
make dev           # Lokal starten (auto-reload)
make run           # Lokal starten (ohne reload)
make install       # Dependencies installieren
make clean         # Cache-Dateien löschen
```

### Docker
```bash
make build         # Image bauen
make up            # Container starten
make down          # Container stoppen
make restart       # Container neustarten
make logs          # Logs anzeigen (follow)
make shell         # Shell im Container
```

### Database
```bash
make migrate       # v1 → v2 Migration
make migrate-check # Migrations-Status
make backup        # Backup erstellen
make backup-v1     # v1 Backup
make db-stats      # Statistiken
make db-latest     # Letzter Messwert
```

### Testing
```bash
make test-receiver # Test-Daten senden
make status-app    # App-Status prüfen
make health        # Health-Check
```

## Konfiguration

### .env

```bash
# App
APP_NAME=hc_weda
PORT=5045  # Intern (Docker: 5021:5045)

# MQTT
MQTT_BROKER=10.1.1.119
HA_BASETOPIC=hc_weda

# Wetterstation
DEVICE_SAINLOGIC_WS3500_ENABLED=true
DEVICE_WETTERSTATION_HTTP_PORT=8089
DEVICE_WETTERSTATION_HTTP_URL=/weatherstation
```

### config/devices/wetterstation.yaml

```yaml
device:
  name: "Wetterstation Garten"
  type: "sainlogic-ws3500"
  location: "Garten"
  
datasource:
  type: "http_receiver"
  port: 8089
  url: "/weatherstation"
  format: "ecowitt"
  
mqtt:
  base_topic: "hc_weda/wetterstation"
  publish_fields:
    temp_c: aussentemperatur_c
    humidity: luftfeuchte_prozent
    # ... (siehe wetterstation.yaml)
```

## Berechnete Werte

Die App berechnet automatisch:

- **Gefühlte Temperatur** (Windchill + Hitzeindex + Solar)
- **Beaufort-Skala** (0-12) mit Text
- **Windrichtung** (N, NO, O, SO, S, SW, W, NW)
- **Taupunkt** (aus Temperatur + Luftfeuchte)
- **Temperatur-Differenz** (Innen/Außen)
- **Lüftungsempfehlung** (basierend auf Temp + Luftfeuchte)
- **Frostwarnung** (bei ≤ 3°C)
- **Solar-Strahlung** (W/m² → Klux)

## Troubleshooting

### Keine Daten von Wetterstation

```bash
# 1. Prüfe ob App läuft
make status-app

# 2. Prüfe Logs
make logs

# 3. Teste Receiver manuell
make test-receiver

# 4. Prüfe Wetterstation-Konfiguration
# → Server-IP: <server-ip>
# → Port: 8089
# → Pfad: /weatherstation
```

### Migration fehlgeschlagen

```bash
# v1 DB prüfen
ls -lh /dockerapps/apps_v1/hc_weda/data/history.db

# Migration erneut ausführen
make migrate

# Status prüfen
make migrate-check
```

### Dashboard zeigt keine Daten

```bash
# Letzten Messwert prüfen
make db-latest

# Health-Check
make health

# Logs prüfen
make logs
```

## Code Quality

```bash
./check.sh          # Prüfen (ruff)
./check.sh --fix    # Auto-Fix
./check.sh --save   # Ergebnis speichern
```

## Architektur

```
hc_weda/
├── app/
│   ├── adapters/
│   │   ├── base.py                    # Basis-Adapter
│   │   ├── sainlogic_ws3500.py        # Wetterstation-Adapter
│   │   └── factory.py                 # Adapter-Factory
│   ├── api/routes/
│   │   ├── weather_receiver.py        # HTTP Receiver
│   │   ├── devices.py                 # Geräte-API
│   │   └── dashboard.py               # Dashboard-API
│   ├── models/
│   │   └── weather.py                 # Datenmodell
│   ├── services/
│   │   ├── database.py                # SQLite
│   │   └── device_manager.py          # Geräte-Verwaltung
│   └── main.py                        # FastAPI App
├── config/devices/
│   └── wetterstation.yaml             # Geräte-Config
├── data/
│   └── weather.db                     # SQLite DB
├── scripts/
│   └── migrate_v1_to_v2.py            # Migrations-Script
└── frontend/                          # v1 Dashboard (unverändert)
```

## Links

- **Dashboard**: http://10.1.1.119:5021
- **Health**: http://10.1.1.119:5021/api/health
- **Weather Receiver**: http://10.1.1.119:8089/weatherstation
- **MQTT Topic**: `hc_weda/wetterstation`
- **Home Assistant Webhook**: `hc_weda`
