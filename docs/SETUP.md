# hc_weda v2 Setup auf Ubuntu Server

## Voraussetzungen

- Ubuntu Server mit SSH-Zugriff
- Python 3.12+ mit venv
- SQLite3
- v1 Datenbank: `/dockerapps/apps_v1/hc_weda/data/history.db`

## Setup-Schritte

### 1. SSH auf Server verbinden

```bash
ssh root@10.1.1.119
```

### 2. Zum Projekt-Verzeichnis wechseln

```bash
cd /dockerapps/apps_v2/hc_weda
```

### 3. Virtual Environment aktivieren

```bash
source ../.venv/bin/activate
```

### 4. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 5. v1 Backup erstellen (WICHTIG!)

```bash
cp /dockerapps/apps_v1/hc_weda/data/history.db \
   /dockerapps/apps_v1/hc_weda/data/history.db.backup_$(date +%Y%m%d_%H%M%S)

# Backup verifizieren
ls -lh /dockerapps/apps_v1/hc_weda/data/history.db*
```

### 6. Migration ausführen

```bash
python scripts/migrate_v1_to_v2.py
```

**Erwartete Ausgabe:**
```
Migration: v1 → v2
  v1: /dockerapps/apps_v1/hc_weda/data/history.db
  v2: /dockerapps/apps_v2/hc_weda/data/weather.db

📊 v1 Datenbank: 980,473 Messungen
📊 v2 Datenbank: 0 Messungen (vor Migration)

🔄 Starte Migration (Batch-Größe: 10,000)...
  10,000 / 980,473 (1.0%) - Migriert: 10,000, Übersprungen: 0
  ...
  980,473 / 980,473 (100.0%) - Migriert: 980,473, Übersprungen: 0

✅ Migration abgeschlossen!
  Neue Datensätze: 980,473
  v2 Datenbank: 980,473 Messungen (nach Migration)

  Zeitraum: 2024-04-20 18:37:00 bis 2026-05-09 10:46:32
```

**Dauer**: ~2-5 Minuten für 1 Million Datensätze

### 7. Migration verifizieren

```bash
# Makefile verwenden
make migrate-check

# Oder manuell:
sqlite3 data/weather.db "SELECT COUNT(*) FROM measurements"
sqlite3 data/weather.db "SELECT MIN(dateutc), MAX(dateutc) FROM measurements"
```

### 8. App lokal testen

```bash
# Mit auto-reload starten
make dev

# In anderem Terminal: Test-Daten senden
make test-receiver
```

**Erwartete Ausgabe:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5045 (Press CTRL+C to quit)
```

**Dashboard öffnen**: http://10.1.1.119:5045

### 9. Docker Build & Deploy

```bash
# Image bauen
make build

# Container starten
make up

# Logs prüfen
make logs

# Status prüfen
make ps
```

**Dashboard (Production)**: http://10.1.1.119:5021

## Verifikation

### Health Check

```bash
curl http://localhost:5045/api/health | jq
```

**Erwartete Antwort:**
```json
{
  "status": "healthy",
  "app": "hc_weda",
  "version": "1.0.0"
}
```

### Geräte-Status

```bash
curl http://localhost:5045/api/devices | jq
```

**Erwartete Antwort:**
```json
{
  "devices": [
    {
      "device_id": "ips-ws3500",
      "name": "Wetterstation Garten",
      "type": "sainlogic-ws3500",
      "online": true
    }
  ]
}
```

### Letzter Messwert

```bash
make db-latest
```

**Erwartete Ausgabe:**
```
2026-05-09 12:52:00|15.2|65|5.2|1013.5
```

### Test-Daten senden

```bash
curl -X GET "http://localhost:5045/weatherstation?tempf=68.5&humidity=65&windspeedmph=5.2&winddir=180&baromin=29.92&dailyrainin=0.5&solarradiation=450&uv=3&indoortempf=72&indoorhumidity=55&dateutc=2026-05-09+14:30:00" | jq
```

**Erwartete Antwort:**
```json
{
  "status": "ok",
  "timestamp": "2026-05-09 14:30:00",
  "data": {
    "temp_c": 20.3,
    "feels_like_c": 20.1,
    "humidity": 65,
    "wind_kmh": 8.4,
    "pressure_hpa": 1013.2,
    "rain_daily_mm": 12.7
  }
}
```

## Wetterstation konfigurieren

Die Wetterstation muss Daten an den Server senden:

1. **Wetterstation-Webinterface** öffnen
2. **Wunderground/Ecowitt Upload** konfigurieren:
   - Server: `10.1.1.119`
   - Port: `8089`
   - Pfad: `/weatherstation`
   - Intervall: `60` Sekunden

## Troubleshooting

### Migration schlägt fehl

```bash
# v1 DB prüfen
ls -lh /dockerapps/apps_v1/hc_weda/data/history.db

# Berechtigungen prüfen
chmod 644 /dockerapps/apps_v1/hc_weda/data/history.db

# DB-Integrität prüfen
sqlite3 /dockerapps/apps_v1/hc_weda/data/history.db "PRAGMA integrity_check"

# Migration erneut ausführen
python scripts/migrate_v1_to_v2.py
```

### App startet nicht

```bash
# Logs prüfen
make logs

# Port prüfen
lsof -i:5045

# Dependencies prüfen
pip list | grep -E "fastapi|uvicorn|pydantic"
```

### Keine Daten von Wetterstation

```bash
# Receiver-Port prüfen
lsof -i:8089

# Logs live verfolgen
make logs

# Test-Daten senden
make test-receiver
```

### MQTT funktioniert nicht

```bash
# MQTT Broker prüfen
mosquitto_sub -h 10.1.1.119 -t "hc_weda/#" -v

# .env prüfen
grep MQTT .env
```

## Rollback zu v1

Falls v2 nicht funktioniert:

```bash
# v2 stoppen
cd /dockerapps/apps_v2/hc_weda
make down

# v1 starten
cd /dockerapps/apps_v1/hc_weda
docker-compose up -d
```

Die v1 Datenbank bleibt unverändert!

## Nächste Schritte

Nach erfolgreicher Migration:

1. ✅ v2 App läuft stabil
2. ✅ Wetterstation sendet Daten an v2
3. ✅ MQTT funktioniert
4. ✅ Dashboard zeigt aktuelle Daten
5. ⏸️ v1 App stoppen (wenn v2 stabil läuft)
6. 📦 v1 Backup aufbewahren

## Monitoring

```bash
# App-Status
make status-app

# Logs live
make logs

# DB-Statistiken
make db-stats

# Letzter Messwert
make db-latest

# Health-Check
make health
```

## Support

Bei Problemen:
- Logs: `make logs`
- Status: `make status-app`
- DB-Check: `make db-check`
- Migration-Status: `make migrate-check`
