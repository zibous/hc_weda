# Deployment v2 → Produktiv

## Übersicht

Diese Anleitung beschreibt, wie hc_weda v2 produktiv gesetzt wird und v1 ersetzt.

## Voraussetzungen

- ✅ v2 ist getestet und funktioniert
- ✅ Dashboard läuft und zeigt Daten an
- ✅ Datenbank ist migriert (980,483 Messungen)
- ✅ Alle API-Endpoints funktionieren

## Deployment-Schritte

### 1. v1 stoppen

```bash
cd /dockerapps/apps_v1/hc_weda
docker-compose down
```

**Wichtig:** v1 läuft auf Port 8090 (Dashboard). Dieser Port wird nach dem Stoppen frei.

### 2. Wetterstation umkonfigurieren

Die Wetterstation muss auf den neuen Port umgestellt werden:

**Alte Konfiguration (v1):**
- URL: `http://10.1.0.119:8090/weatherstation`
- Port: 8090

**Neue Konfiguration (v2):**
- URL: `http://10.1.0.119:8089/weatherstation`
- Port: 8089

**Wie umstellen:**
1. Wetterstation Web-Interface öffnen (IP-Adresse der Station im Browser)
2. Zu "Customized" oder "Weather Services" navigieren
3. Ecowitt/Wunderground Server-URL ändern:
   - Server: `10.1.0.119`
   - Port: `8089`
   - Path: `/weatherstation`
4. Speichern und Station neu starten

### 3. v2 Docker-Container bauen

```bash
cd /dockerapps/apps_v2/hc_weda
make build
```

**Was passiert:**
- Dockerfile wird gebaut
- Python-Dependencies werden installiert
- App wird in Container gepackt

### 4. v2 starten

```bash
make up
```

**Was passiert:**
- Container startet im Hintergrund
- Ports werden gemappt:
  - `5021:5045` - Dashboard (extern:intern)
  - `8089:8089` - Wetterstation HTTP Receiver
- Volumes werden gemountet (data, config, frontend, logs)
- Healthcheck wird aktiviert

### 5. Logs prüfen

```bash
make logs
```

**Erwartete Ausgabe:**
```
hc_weda v1.0.0 starting
Datenbank initialisiert
Device Manager: 1 Geräte geladen
App-Status publiziert: online (mit LWT)
HA Discovery: App-Status Sensor publiziert
HA Discovery: Wetterstation Garten publiziert
Application startup complete.
Uvicorn running on http://0.0.0.0:5045
```

### 6. Dashboard testen

**URLs:**
- Dashboard: `http://10.1.0.119:5021/`
- API Health: `http://10.1.0.119:5021/api/health`
- API Current: `http://10.1.0.119:5021/api/current`

**Tests:**
```bash
# Health Check
curl http://10.1.0.119:5021/api/health
# Erwartete Ausgabe: {"status":"ok","app":"hc_weda","version":"1.0.0"}

# Geräte
curl http://10.1.0.119:5021/api/devices | jq

# Aktuelle Daten
curl http://10.1.0.119:5021/api/current | jq

# DB-Statistiken
curl http://10.1.0.119:5021/api/dbstats | jq
```

### 7. Wetterstation-Daten prüfen

**Warten auf ersten Datensatz:**
- Wetterstation sendet alle 16 Sekunden Daten
- Nach ca. 30 Sekunden sollte der erste Datensatz ankommen

**Logs prüfen:**
```bash
make logs
```

**Erwartete Ausgabe:**
```
INFO: 10.1.0.119:xxxxx - "GET /weatherstation?tempf=75.2&humidity=51&... HTTP/1.1" 200 OK
```

**Datenbank prüfen:**
```bash
make db-latest
```

**Erwartete Ausgabe:**
```
2026-05-09 14:30:00|24.0|51|2.6|1003.7
```

### 8. Home Assistant prüfen

**MQTT Topics:**
- `hc_weda/status` - App-Status
- `hc_weda/wetterstation/state` - Wetterdaten

**Home Assistant Entities:**
- `sensor.hc_weda_status` - App-Status
- `sensor.wetterstation_garten_temperature` - Temperatur
- `sensor.wetterstation_garten_humidity` - Luftfeuchte
- `sensor.wetterstation_garten_pressure` - Luftdruck
- ... (weitere Sensoren)

**Prüfen:**
1. Home Assistant öffnen
2. Entwicklertools → Zustände
3. Nach "wetterstation" suchen
4. Sensoren sollten aktuelle Werte anzeigen

## Port-Übersicht

| Service | v1 Port | v2 Port (extern) | v2 Port (intern) |
|---------|---------|------------------|------------------|
| Dashboard | 8090 | 5021 | 5045 |
| Weather Receiver | 8090 | 8089 | 8089 |

**Wichtig:** 
- v1 Dashboard lief auf Port 8090
- v2 Dashboard läuft auf Port 5021 (extern) / 5045 (intern)
- v2 Weather Receiver läuft auf Port 8089

## Rollback (falls nötig)

Falls v2 nicht funktioniert, kann v1 wieder gestartet werden:

```bash
# v2 stoppen
cd /dockerapps/apps_v2/hc_weda
make down

# v1 starten
cd /dockerapps/apps_v1/hc_weda
docker-compose up -d

# Wetterstation zurück auf Port 8090 konfigurieren
```

## Monitoring

### Container-Status prüfen

```bash
docker ps | grep hc_weda
```

**Erwartete Ausgabe:**
```
CONTAINER ID   IMAGE       STATUS                    PORTS
abc123def456   hc_weda     Up 5 minutes (healthy)    0.0.0.0:5021->5045/tcp, 0.0.0.0:8089->8089/tcp
```

### Logs live verfolgen

```bash
make logs-follow
```

### Datenbank-Statistiken

```bash
make db-stats
```

**Erwartete Ausgabe:**
```
Datenbank: data/weather.db
Messungen: 980,483
Ältester Eintrag: 2024-04-20 18:37:00
Neuester Eintrag: 2026-05-09 14:30:00
```

### Container neu starten

```bash
make restart
```

## Troubleshooting

### Problem: Container startet nicht

**Lösung:**
```bash
# Logs prüfen
make logs

# Container neu bauen
make build
make up
```

### Problem: Keine Daten von Wetterstation

**Prüfen:**
1. Wetterstation-Konfiguration (Port 8089?)
2. Netzwerk-Verbindung (Ping 10.1.0.119)
3. Logs: `make logs`
4. Firewall-Regeln

**Test:**
```bash
# Manueller Test-Request
curl "http://10.1.0.119:8089/weatherstation?tempf=75.2&humidity=51&windspeedmph=1.6&winddir=180&baromin=29.64&dailyrainin=0.0&solarradiation=450&uv=3&indoortempf=72&indoorhumidity=55&dateutc=2026-05-09+14:30:00"
```

### Problem: Dashboard zeigt keine Daten

**Prüfen:**
1. API-Endpoints: `curl http://10.1.0.119:5021/api/current`
2. Browser-Console (F12) auf Fehler prüfen
3. Datenbank: `make db-latest`

### Problem: Home Assistant zeigt keine Sensoren

**Prüfen:**
1. MQTT-Verbindung: `make logs | grep MQTT`
2. HA Discovery Topics: `mosquitto_sub -h 10.1.1.119 -t "homeassistant/#" -v`
3. HA Logs: Einstellungen → System → Protokolle

## Backup

### Datenbank sichern

```bash
# Manuelles Backup
cp data/weather.db data/weather.db.backup_$(date +%Y%m%d_%H%M%S)

# Automatisches Backup (Cron)
# Siehe: backup_dockerapps.sh
```

### Konfiguration sichern

```bash
# Gesamtes Verzeichnis sichern
tar -czf hc_weda_backup_$(date +%Y%m%d).tar.gz \
  /dockerapps/apps_v2/hc_weda \
  --exclude='data/weather.db' \
  --exclude='logs/*' \
  --exclude='.venv'
```

## Nächste Schritte

1. ✅ v2 produktiv gesetzt
2. ⏳ v1 nach 1 Woche Testphase löschen
3. ⏳ Wettervorhersage implementieren (optional)
4. ⏳ Monitoring einrichten (Grafana, Prometheus)

## Kontakt

Bei Problemen:
- Logs prüfen: `make logs`
- Status prüfen: `make status`
- Container neu starten: `make restart`

---

**Deployment durchgeführt am:** 2026-05-09
**Version:** hc_weda v2.0.0
**Status:** ✅ Bereit für Produktiv-Einsatz
