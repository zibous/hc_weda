# hc_weda v2 Test-Checkliste

## Vor dem Test

- [ ] SSH-Verbindung zum Server: `ssh root@10.1.1.119`
- [ ] Im Projekt-Verzeichnis: `cd /dockerapps/apps_v2/hc_weda`
- [ ] Virtual Environment aktiviert: `source ../.venv/bin/activate`
- [ ] Dependencies installiert: `pip install -r requirements.txt`

## Migration

- [ ] v1 Backup erstellt: `cp /dockerapps/apps_v1/hc_weda/data/history.db /dockerapps/apps_v1/hc_weda/data/history.db.backup_$(date +%Y%m%d_%H%M%S)`
- [ ] Backup verifiziert: `ls -lh /dockerapps/apps_v1/hc_weda/data/history.db*`
- [ ] Migration ausgeführt: `python scripts/migrate_v1_to_v2.py`
- [ ] Migration erfolgreich: Siehe Ausgabe "✅ Migration abgeschlossen!"
- [ ] Datensätze korrekt: `make migrate-check`

## Lokaler Test (make dev)

### App-Start

- [ ] App gestartet: `make dev`
- [ ] Keine Fehler beim Start
- [ ] Logs zeigen: "Application startup complete"
- [ ] Device Manager: "1 Geräte geladen"
- [ ] Port 5045 läuft: `lsof -i:5045`

### Health Check

```bash
curl http://localhost:5045/api/health | jq
```

- [ ] Status: `"healthy"`
- [ ] App: `"hc_weda"`
- [ ] Version: `"1.0.0"`

### Geräte-Status

```bash
curl http://localhost:5045/api/devices | jq
```

- [ ] 1 Gerät vorhanden
- [ ] device_id: `"ips-ws3500"`
- [ ] name: `"Wetterstation Garten"`
- [ ] type: `"sainlogic-ws3500"`
- [ ] online: `true` (wenn letzte Daten < 15 Min)

### Dashboard

```bash
curl http://localhost:5045/ | head -20
```

- [ ] HTML-Seite wird geladen
- [ ] Kein 404 oder 500 Fehler

### Test-Daten senden

```bash
curl -X GET "http://localhost:5045/weatherstation?tempf=68.5&humidity=65&windspeedmph=5.2&winddir=180&baromin=29.92&dailyrainin=0.5&solarradiation=450&uv=3&indoortempf=72&indoorhumidity=55&dateutc=2026-05-09+14:30:00" | jq
```

- [ ] Status: `"ok"`
- [ ] timestamp vorhanden
- [ ] temp_c: ~20.3°C
- [ ] humidity: 65
- [ ] wind_kmh: ~8.4
- [ ] pressure_hpa: ~1013

### Datenbank prüfen

```bash
make db-latest
```

- [ ] Letzter Messwert wird angezeigt
- [ ] Zeitstempel aktuell
- [ ] Werte plausibel

```bash
make db-stats
```

- [ ] Anzahl Messungen: ~980.000+
- [ ] Zeitraum: 2024-04-20 bis heute
- [ ] DB-Größe: ~300-400 MB

### MQTT prüfen (optional)

```bash
mosquitto_sub -h 10.1.1.119 -t "hc_weda/#" -v
```

- [ ] Topic: `hc_weda/wetterstation`
- [ ] Payload enthält deutsche Feldnamen
- [ ] Werte plausibel

### Logs prüfen

- [ ] Keine ERROR-Meldungen
- [ ] Keine WARNING-Meldungen (außer "MQTT nicht verfügbar" wenn Broker aus)
- [ ] INFO-Meldungen zeigen normale Aktivität

### App stoppen

- [ ] Ctrl+C drücken
- [ ] App stoppt sauber
- [ ] Keine Fehler beim Shutdown

## Docker Test (make up)

### Build

```bash
make build
```

- [ ] Build erfolgreich
- [ ] Keine Fehler
- [ ] Image erstellt: `docker images | grep hc_weda`

### Start

```bash
make up
```

- [ ] Container startet: `docker ps | grep hc_weda`
- [ ] Status: "Up"
- [ ] Ports: `5021:5045`, `8089:8089`

### Logs

```bash
make logs
```

- [ ] "Application startup complete"
- [ ] "Device Manager: 1 Geräte geladen"
- [ ] "WeatherDB initialisiert"
- [ ] Keine ERROR-Meldungen

### Health Check (Docker)

```bash
curl http://localhost:5021/api/health | jq
```

- [ ] Status: `"healthy"`
- [ ] Erreichbar über Port 5021 (extern)

### Dashboard (Docker)

Browser öffnen: `http://10.1.1.119:5021`

- [ ] Dashboard lädt
- [ ] Keine 404 oder 500 Fehler
- [ ] Wetterdaten werden angezeigt (wenn vorhanden)

### Test-Daten (Docker)

```bash
curl -X GET "http://localhost:5021/weatherstation?tempf=68.5&humidity=65&windspeedmph=5.2&winddir=180&baromin=29.92&dailyrainin=0.5&solarradiation=450&uv=3&indoortempf=72&indoorhumidity=55&dateutc=2026-05-09+15:00:00" | jq
```

- [ ] Status: `"ok"`
- [ ] Daten werden verarbeitet

### Container-Shell

```bash
make shell
```

- [ ] Shell öffnet sich
- [ ] `ls -la` zeigt Dateien
- [ ] `cat .env` zeigt Konfiguration
- [ ] `exit` zum Verlassen

### Healthcheck (Docker intern)

```bash
docker inspect hc_weda | jq '.[0].State.Health'
```

- [ ] Status: `"healthy"`
- [ ] FailingStreak: 0

## Wetterstation-Integration

### Wetterstation konfigurieren

- [ ] Wetterstation-Webinterface geöffnet
- [ ] Wunderground/Ecowitt Upload konfiguriert:
  - Server: `10.1.1.119`
  - Port: `8089`
  - Pfad: `/weatherstation`
  - Intervall: `60` Sekunden
- [ ] Konfiguration gespeichert

### Daten-Empfang prüfen

```bash
make logs
```

- [ ] Logs zeigen eingehende Requests: `GET /weatherstation`
- [ ] Status: `200 OK`
- [ ] "Wetterdaten gespeichert" Meldungen
- [ ] Keine Fehler

### Aktuelle Daten

```bash
make db-latest
```

- [ ] Zeitstempel aktuell (< 2 Minuten alt)
- [ ] Werte plausibel (Temperatur, Luftfeuchte, etc.)

## Performance

- [ ] App-Start: < 5 Sekunden
- [ ] Health-Check: < 100ms
- [ ] Daten-Empfang: < 200ms
- [ ] Dashboard-Laden: < 1 Sekunde
- [ ] Migration: 2-5 Minuten für 1 Million Datensätze

## Cleanup

- [ ] Test-Container gestoppt: `make down` (wenn nicht produktiv)
- [ ] Logs gesichert (falls Fehler auftraten)
- [ ] v1 Backup aufbewahrt

## Produktiv-Freigabe

Wenn alle Tests erfolgreich:

- [ ] v2 läuft stabil (mindestens 24h)
- [ ] Wetterstation sendet Daten zuverlässig
- [ ] MQTT funktioniert
- [ ] Dashboard zeigt aktuelle Daten
- [ ] Keine Fehler in Logs
- [ ] v1 kann gestoppt werden

## Rollback-Plan

Falls Probleme auftreten:

```bash
# v2 stoppen
cd /dockerapps/apps_v2/hc_weda
make down

# v1 starten
cd /dockerapps/apps_v1/hc_weda
docker-compose up -d
```

## Notizen

Hier Notizen zu Problemen oder Beobachtungen eintragen:

```
Datum: ___________
Problem: _________________________________________
Lösung: __________________________________________

Datum: ___________
Problem: _________________________________________
Lösung: __________________________________________
```
