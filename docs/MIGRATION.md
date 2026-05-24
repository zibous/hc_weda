# Migration von hc_weda v1 → v2

## Übersicht

Dieses Dokument beschreibt die Migration der Wetterdaten von **hc_weda v1** nach **hc_weda v2**.

### Was wird migriert?

- ✅ **Alle Wetterdaten** aus `apps_v1/hc_weda/data/history.db`
- ✅ **Zeitraum**: April 2024 bis heute (~980.000 Messungen)
- ✅ **Datenstruktur**: Kompatibel mit v1 Schema + neue v2 Felder

### Was ändert sich?

| Aspekt | v1 | v2 |
|--------|----|----|
| **Datenbank** | `history.db` | `weather.db` |
| **Tabelle** | `measurements` | `measurements` (erweitert) |
| **Schema** | Imperial + Metrisch | Imperial + Metrisch + Zusatzfelder |
| **Neue Felder** | - | `feels_like_c`, `beaufort`, `climate_advice`, etc. |

## Migrations-Schritte

### 1. Backup erstellen (WICHTIG!)

```bash
# v1 Datenbank sichern
cp /dockerapps/apps_v1/hc_weda/data/history.db \
   /dockerapps/apps_v1/hc_weda/data/history.db.backup
```

### 2. Migration ausführen

```bash
cd /dockerapps/apps_v2/hc_weda

# Mit Standardpfaden
python scripts/migrate_v1_to_v2.py

# Oder mit benutzerdefinierten Pfaden
python scripts/migrate_v1_to_v2.py \
  --v1-db /dockerapps/apps_v1/hc_weda/data/history.db \
  --v2-db /dockerapps/apps_v2/hc_weda/data/weather.db
```

**Ausgabe:**
```
Migration: v1 → v2
  v1: /dockerapps/apps_v1/hc_weda/data/history.db
  v2: /dockerapps/apps_v2/hc_weda/data/weather.db

📊 v1 Datenbank: 980,473 Messungen
📊 v2 Datenbank: 0 Messungen (vor Migration)

🔄 Starte Migration (Batch-Größe: 10,000)...
  10,000 / 980,473 (1.0%) - Migriert: 10,000, Übersprungen: 0
  20,000 / 980,473 (2.0%) - Migriert: 20,000, Übersprungen: 0
  ...
  980,473 / 980,473 (100.0%) - Migriert: 980,473, Übersprungen: 0

✅ Migration abgeschlossen!
  Neue Datensätze: 980,473
  v2 Datenbank: 980,473 Messungen (nach Migration)

  Zeitraum: 2024-04-20 18:37:00 bis 2026-05-09 10:46:32
```

### 3. Migration verifizieren

```bash
# Anzahl Datensätze prüfen
sqlite3 /dockerapps/apps_v2/hc_weda/data/weather.db \
  "SELECT COUNT(*) FROM measurements"

# Zeitraum prüfen
sqlite3 /dockerapps/apps_v2/hc_weda/data/weather.db \
  "SELECT MIN(dateutc), MAX(dateutc) FROM measurements"

# Beispiel-Datensatz anzeigen
sqlite3 /dockerapps/apps_v2/hc_weda/data/weather.db \
  "SELECT * FROM measurements ORDER BY dateutc DESC LIMIT 1"
```

### 4. v2 App starten

```bash
cd /dockerapps/apps_v2/hc_weda

# Docker-Build
make build

# Docker starten
make up

# Logs prüfen
make logs
```

## Datenbank-Schema

### v1 Schema (history.db)

```sql
CREATE TABLE measurements (
    dateutc         TEXT PRIMARY KEY,
    device          TEXT,
    station_id      TEXT,
    -- Imperial
    indoortempf, tempf, dewptf, windchillf,
    indoorhumidity, humidity,
    windspeedmph, windgustmph, winddir,
    absbaromin, baromin,
    rainin, dailyrainin, weeklyrainin, monthlyrainin,
    solarradiation, uv,
    -- Metrisch
    indoor_temp_c, temp_c, dewpoint_c, windchill_c,
    windspeed_kmh, windgust_kmh,
    abs_pressure_hpa, pressure_hpa,
    rain_mm, daily_rain_mm, weekly_rain_mm, monthly_rain_mm,
    -- Meta
    softwaretype, date_local
);
```

### v2 Schema (weather.db)

```sql
CREATE TABLE measurements (
    -- Alle v1 Felder +
    -- Zusätzliche berechnete Werte
    feels_like_c    REAL,        -- Gefühlte Temperatur
    wind_dir_text   TEXT,        -- Windrichtung (N, NO, O, ...)
    beaufort        INTEGER,     -- Beaufort-Skala (0-12)
    beaufort_text   TEXT,        -- Beaufort-Text
    temp_diff_c     REAL,        -- Temperatur-Differenz Innen/Außen
    climate_advice  TEXT,        -- Lüftungsempfehlung
    frost_text      TEXT,        -- Frostwarnung
    solar_klux      REAL         -- Solar-Strahlung in Klux
);
```

## Sicherheit

- ✅ **v1 Datenbank bleibt unverändert** (Read-Only Zugriff)
- ✅ **Keine Daten gehen verloren** (INSERT OR REPLACE)
- ✅ **Duplikate werden übersprungen**
- ✅ **Batch-Verarbeitung** (10.000 Zeilen pro Batch)
- ✅ **Fortschrittsanzeige** während Migration

## Rollback

Falls v2 nicht funktioniert, kann v1 jederzeit wieder gestartet werden:

```bash
cd /dockerapps/apps_v1/hc_weda
docker-compose up -d
```

Die v1 Datenbank bleibt unverändert!

## Troubleshooting

### Migration schlägt fehl

```bash
# Prüfe ob v1 DB existiert
ls -lh /dockerapps/apps_v1/hc_weda/data/history.db

# Prüfe Berechtigungen
chmod 644 /dockerapps/apps_v1/hc_weda/data/history.db

# Prüfe DB-Integrität
sqlite3 /dockerapps/apps_v1/hc_weda/data/history.db "PRAGMA integrity_check"
```

### v2 DB ist leer

```bash
# Migration erneut ausführen (überschreibt keine Daten)
python scripts/migrate_v1_to_v2.py
```

### Speicherplatz prüfen

```bash
# v1 DB Größe
du -h /dockerapps/apps_v1/hc_weda/data/history.db

# v2 DB Größe
du -h /dockerapps/apps_v2/hc_weda/data/weather.db

# Verfügbarer Speicher
df -h /dockerapps
```

## Performance

- **Migrations-Dauer**: ~2-5 Minuten für 1 Million Datensätze
- **Batch-Größe**: 10.000 Zeilen (anpassbar mit `--batch-size`)
- **DB-Größe**: v2 DB ist ~gleich groß wie v1 DB

## Nächste Schritte

Nach erfolgreicher Migration:

1. ✅ v2 App testen (Dashboard, MQTT, Webhooks)
2. ✅ Neue Wetterdaten empfangen (Wetterstation → v2)
3. ✅ v1 App stoppen (wenn v2 stabil läuft)
4. ✅ v1 Backup aufbewahren (für Notfälle)

## Support

Bei Problemen:
- Logs prüfen: `docker logs hc_weda`
- DB-Statistiken: `python scripts/migrate_v1_to_v2.py --help`
- v1 Backup wiederherstellen: `cp history.db.backup history.db`
