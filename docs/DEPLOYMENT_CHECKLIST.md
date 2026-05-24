# Deployment Checkliste v2 → Produktiv

## Pre-Deployment

- [x] v2 getestet (make dev)
- [x] Dashboard funktioniert
- [x] Alle Tabs funktionieren (Aktuell, Heute, Verlauf, Statistik)
- [x] Datenbank migriert (980,483 Messungen)
- [x] API-Endpoints getestet
- [x] Docker-Konfiguration geprüft

## Deployment

### Schritt 1: v1 stoppen

```bash
cd /dockerapps/apps_v1/hc_weda
docker-compose down
```

- [ ] v1 Container gestoppt
- [ ] Port 8090 ist frei

### Schritt 2: Wetterstation umkonfigurieren

**Wetterstation Web-Interface öffnen:**
- [ ] IP-Adresse der Wetterstation im Browser öffnen
- [ ] Zu "Customized" oder "Weather Services" navigieren
- [ ] Server-URL ändern:
  - Server: `10.1.0.119`
  - Port: `8089`
  - Path: `/weatherstation`
- [ ] Speichern
- [ ] Wetterstation neu starten (optional)

### Schritt 3: v2 bauen und starten

```bash
cd /dockerapps/apps_v2/hc_weda
make build
make up
```

- [ ] Docker-Image gebaut
- [ ] Container gestartet
- [ ] Keine Fehler in den Logs

### Schritt 4: Logs prüfen

```bash
make logs
```

**Erwartete Ausgabe:**
- [ ] "hc_weda v1.0.0 starting"
- [ ] "Datenbank initialisiert"
- [ ] "Device Manager: 1 Geräte geladen"
- [ ] "App-Status publiziert: online"
- [ ] "HA Discovery: Wetterstation Garten publiziert"
- [ ] "Application startup complete"

### Schritt 5: Dashboard testen

**Browser öffnen:** `http://10.1.0.119:5021/`

- [ ] Dashboard lädt
- [ ] CSS und JavaScript werden geladen
- [ ] Keine Fehler in Browser-Console (F12)
- [ ] Daten werden angezeigt

**API testen:**
```bash
curl http://10.1.0.119:5021/api/health
curl http://10.1.0.119:5021/api/current | jq
curl http://10.1.0.119:5021/api/dbstats | jq
```

- [ ] Health Check: `{"status":"ok"}`
- [ ] Current: Zeigt aktuelle Daten
- [ ] DBStats: Zeigt 980,483+ Messungen

### Schritt 6: Wetterstation-Daten prüfen

**Warten:** 30-60 Sekunden (Wetterstation sendet alle 16 Sekunden)

```bash
make logs
```

- [ ] Log-Eintrag: "GET /weatherstation?tempf=... HTTP/1.1" 200 OK
- [ ] Keine Fehler beim Daten-Empfang

```bash
make db-latest
```

- [ ] Neuester Datensatz zeigt aktuelles Datum/Zeit
- [ ] Werte sind plausibel

### Schritt 7: Home Assistant prüfen

**Home Assistant öffnen:**
- [ ] Entwicklertools → Zustände
- [ ] Nach "wetterstation" suchen
- [ ] Sensoren zeigen aktuelle Werte
- [ ] Keine "unavailable" Sensoren

**MQTT prüfen (optional):**
```bash
mosquitto_sub -h 10.1.1.119 -u smarthome -P seOnly4Me -t "hc_weda/#" -v
```

- [ ] Topic `hc_weda/status` zeigt "online"
- [ ] Topic `hc_weda/wetterstation/state` zeigt Wetterdaten

## Post-Deployment

### Monitoring (erste 24 Stunden)

- [ ] Stündlich Logs prüfen: `make logs`
- [ ] Dashboard regelmäßig öffnen
- [ ] Home Assistant Sensoren prüfen
- [ ] Datenbank-Wachstum prüfen: `make db-stats`

### Nach 1 Woche

- [ ] v2 läuft stabil
- [ ] Keine Fehler in Logs
- [ ] Alle Daten werden korrekt empfangen
- [ ] Dashboard funktioniert einwandfrei
- [ ] v1 kann gelöscht werden

### v1 aufräumen (nach erfolgreicher Testphase)

```bash
cd /dockerapps/apps_v1/hc_weda
docker-compose down
docker rmi hc_weda_v1  # Image löschen (falls vorhanden)

# Optional: v1 Verzeichnis archivieren
cd /dockerapps
tar -czf apps_v1_hc_weda_backup_$(date +%Y%m%d).tar.gz apps_v1/hc_weda
# Dann v1 Verzeichnis löschen (VORSICHT!)
```

- [ ] v1 Container gelöscht
- [ ] v1 Image gelöscht
- [ ] v1 Verzeichnis archiviert
- [ ] v1 Verzeichnis gelöscht (optional)

## Rollback-Plan (falls nötig)

Falls v2 nicht funktioniert:

```bash
# v2 stoppen
cd /dockerapps/apps_v2/hc_weda
make down

# v1 starten
cd /dockerapps/apps_v1/hc_weda
docker-compose up -d

# Wetterstation zurück auf Port 8090 konfigurieren
```

- [ ] Rollback-Plan verstanden
- [ ] v1 Backup vorhanden

## Notizen

**Deployment-Datum:** _________________

**Durchgeführt von:** _________________

**Probleme/Besonderheiten:**
```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

**Status:**
- [ ] ✅ Deployment erfolgreich
- [ ] ⚠️ Deployment mit Problemen (siehe Notizen)
- [ ] ❌ Rollback durchgeführt

## Kontakt

Bei Problemen:
- Logs: `make logs`
- Status: `make status`
- Restart: `make restart`
- Dokumentation: `DEPLOYMENT.md`
