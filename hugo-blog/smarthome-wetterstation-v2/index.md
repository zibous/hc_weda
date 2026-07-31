---
title: "🌦️ Wetterstation im Smart Home – Lokale Datenerfassung mit Sainlogic WS3500"
date: 2026-05-08T14:00:00
description: "Lokale Integration einer Sainlogic WS3500 Wetterstation via Ecowitt-Protokoll – mit SQLite-Langzeitarchiv, MQTT, Wetter-Warnsystem und Web-Dashboard."
type: "post"
draft: false
image: "posts/smarthome-wetterstation-v2/wetterdaten.png"
author: "Peter Siebler"
snap_gallery: true
gallery: true
categories:
  - "Smarthome"
tags: ["docker", "python", "fastapi", "mqtt", "homeassistant"]
---

[![GITHUB: HC_SCALE](https://img.shields.io/badge/Project-GitHub-yellow.svg)](https://github.com/zibous/hc_weda)
[![Support author](https://img.shields.io/badge/buy%20me%20a%20coffee-orange.svg)](https://www.buymeacoff.ee/zibous)
[![License](https://img.shields.io/badge/license-Open%20Source-green.svg)](https://opensource.org)
![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)

## Die Wetterstation als permanenter Datenpunkt

Eine Wetterstation liefert im Minutentakt Messdaten – Temperatur, Luftfeuchte, Wind, Regen, Luftdruck, Sonnenstrahlung. Die meisten Besitzer nutzen nur die Cloud-App des Herstellers oder das kleine LCD-Display. Mit **hc_weda** wird daraus ein vollwertiges Langzeit-Archiv mit über einer Million Datenpunkten, einem intelligenten Warnsystem und Home Assistant Integration – komplett lokal, ohne Cloud.

<!--more-->

## Warum eine eigene Lösung?

Die Sainlogic WS3500 unterstützt das **Ecowitt-Protokoll**: Alle 60 Sekunden sendet die Station einen HTTP-Request mit sämtlichen Messwerten an eine frei konfigurierbare IP-Adresse im lokalen Netzwerk. Kein Cloud-Account nötig, keine Abhängigkeit von Drittservern.

Die Vorteile gegenüber Wunderground, Ecowitt-Cloud & Co:

- **Volle Datenhoheit** – alle Messwerte bleiben im eigenen Netzwerk
- **Unbegrenzte Historie** – SQLite speichert jeden einzelnen Messwert (seit April 2024: >1 Million Datenpunkte)
- **Eigene Berechnungen** – gefühlte Temperatur, Beaufort-Skala, Lüftungsempfehlung, Frostwarnung
- **Sofortige Reaktion** – Wetter-Warnungen per Webhook in Echtzeit
- **Keine Rate-Limits** – kein Throttling, kein Token-Handling

---

## 🏗️ Architektur & Datenfluss

Die Anwendung basiert auf FastAPI und arbeitet als passiver HTTP-Receiver: Die Wetterstation schickt die Daten, die App verarbeitet, speichert und verteilt sie.

{{< mermaid >}}
flowchart TD
    Main["main.py (Lifespan)<br>SQLite · DeviceManager · MQTT · Alerts"] --> FastAPI["FastAPI Server :5045"]
    FastAPI --> Receiver["Weather Receiver<br>/weatherstation (GET/POST)"]
    FastAPI --> DashAPI["Dashboard API<br>/api/current · /api/today · /api/range"]
    FastAPI --> KPI["KPI / Health<br>/api/kpidata · /api/forecast"]
    Receiver -->|"alle 60s"| Adapter["Sainlogic WS3500 Adapter<br>Ecowitt parsen · Validieren<br>F→C, in→mm · WeatherReading"]
    Adapter --> DB["SQLite Database<br>data/weather.db"]
    Adapter --> MQTT["MQTT Broker<br>hc_weda/wetterstation/"]
    MQTT --> HA["Home Assistant<br>MQTT Discovery · Webhooks · Warnungen"]
    DB --> Dashboard["Web Dashboard (SPA)<br>Zeitreihen + Statistiken"]
    DB --> Alerts["Weather Alerts<br>Sturm · Starkregen · Frost"]
    DashAPI --> Forecast["Open-Meteo API<br>48h Vorhersage (30min Cache)"]
{{< /mermaid >}}

---

## 🔌 Hardware-Setup

| Komponente | Details |
|------------|---------|
| **Wetterstation** | Sainlogic WS3500 (SAINLOGIC HIGH TECH INNOVATION CO., LIMITED) |
| **Protokoll** | Ecowitt (HTTP GET mit Query-Parametern) |
| **Standort** | Garten (47.46°N, 9.64°O) |
| **Sendeintervall** | 60 Sekunden |
| **Sensoren** | Temperatur (innen/außen), Luftfeuchte, Wind (Geschwindigkeit + Richtung + Böen), Luftdruck, Regen (Rate + Tag + Woche + Monat), Solarstrahlung, UV-Index |

Die Station benötigt nur eine einmalige Konfiguration im WS-View Menü: IP-Adresse des Servers + Port + Pfad. Danach sendet sie autonom.

---

## 📡 Der Datenfluss im Detail

### 1. Empfang (Ecowitt-Protokoll)

Die Wetterstation sendet alle 60 Sekunden einen HTTP GET:

```
GET /weatherstation?tempf=68.5&indoortempf=74.8&humidity=65&indoorhumidity=41
    &windspeedmph=5.2&windgustmph=8.1&winddir=319&baromin=29.637
    &rainin=0.000&dailyrainin=0.012&weeklyrainin=1.5&monthlyrainin=12.4
    &solarradiation=258.98&UV=2&dateutc=2026-07-08+10:15:22
```

### 2. Konvertierung (Imperial → Metrisch)

Der **Sainlogic-Adapter** wandelt alle Werte in SI-Einheiten um:

| Eingang | Umrechnung | Ausgang |
|---------|-----------|---------|
| °F (tempf) | `(F - 32) × 5/9` | °C |
| MPH (windspeedmph) | `× 1.609` | km/h |
| Inches (rainin) | `× 25.4` | mm |
| InHg (baromin) | `× 33.864` | hPa |
| W/m² (solarradiation) | `× 0.0079` | Klux |

### 3. Berechnete Werte

Aus den Rohdaten werden zusätzliche Informationen abgeleitet:

- **Gefühlte Temperatur** – kombiniert Windchill (<10°C), Hitzeindex (>27°C) und Solarstrahlung (>500 W/m²)
- **Beaufort-Skala** (0–12) mit deutschem Text ("Windstille" bis "Orkan")
- **Windrichtung** – Grad → Kompass-Text (N, NO, O, SO, S, SW, W, NW)
- **Taupunkt** – berechnet aus Temperatur + Luftfeuchte
- **Temperatur-Differenz** – Innen minus Außen
- **Lüftungsempfehlung** – "Lüften empfohlen" / "Fenster schließen" / "Raumklima optimal"
- **Frostwarnung** – bei ≤ 3°C Warnung, bei ≤ 0°C Alarm

### 4. Persistierung

Jeder Messwert wird in SQLite gespeichert. Die Datenbank enthält seit April 2024 über **eine Million Datenpunkte** – lückenlos, im Minutentakt.

### 5. MQTT Publishing

Alle Werte werden mit **deutschen Feldnamen** publiziert:

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

### 6. Wetter-Warnungen

Bei Überschreitung definierter Schwellwerte wird sofort ein Webhook an Home Assistant gesendet – ideal für Push-Benachrichtigungen oder Automationen (z.B. Markise einfahren bei Sturm).

---

## ⚠️ Das Wetter-Warnsystem

Das Warnsystem arbeitet mit **Hysterese-Logik**, um nervöses Hin- und Herschalten bei Grenzwerten zu verhindern:

| Warnung | Schwellwert | Aktion |
|---------|-------------|--------|
| **Sturm** | Wind > 50 km/h oder Böen > 70 km/h | Webhook "storm: on" |
| **Starkregen** | Regenrate > 10 mm/h | Webhook "heavy_rain: on" |
| **Frost** | Temperatur ≤ 0°C | Webhook "frost: on" |
| **Frostgefahr** | Temperatur 0–3°C | Webhook "freeze_risk: on" |

**Regeln:**
- Warnung bleibt **mindestens 15 Minuten** aktiv (auch wenn Wert kurz unter Schwellwert fällt)
- Nach Deaktivierung gilt ein **5-Minuten-Cooldown** (verhindert Flapping)
- Jede Aktivierung/Deaktivierung wird via Webhook gemeldet

---

## 🌤️ Open-Meteo Vorhersage

Zusätzlich zu den Live-Daten holt die App eine **48-Stunden-Vorhersage** von der kostenlosen Open-Meteo API:

- Stündliche Auflösung: Temperatur, Niederschlagswahrscheinlichkeit, Wind, Bewölkung, UV-Index
- Aktuelles Wetter mit WMO-Wettercode (→ deutschem Text + Emoji)
- **30-Minuten-Cache** – maximal 48 API-Calls pro Tag
- **Kein API-Key** erforderlich (Open-Data, 10.000 Requests/Tag frei)
- **Backoff-Schutz** bei Rate-Limit (5 Min Pause nach HTTP 429)

Das Dashboard zeigt die Vorhersage als Zeitreihe neben den aktuellen Messwerten an.

---

## 🖥️ Web Dashboard

Das integrierte Dashboard bietet:

- **Aktuelle Werte** – Temperatur, Luftfeuchte, Wind, Regen, Luftdruck, Solar als Tiles
- **Tagesverlauf** – Zeitreihen-Grafiken für alle Messgrößen
- **Tages-Zusammenfassung** – Min/Max/Avg mit Trend-Pfeilen (↑↓→)
- **Historische Statistiken** – Tages-Aggregation über beliebige Zeiträume
- **Monatliche Regensummen** – 13-Monats-Übersicht
- **Vorhersage** – 48h-Prognose mit Icons und Temperaturverlauf
- **Downsampling** – bei großen Zeiträumen automatische Reduktion auf max. 1000 Datenpunkte

---

## 🔗 Home Assistant Integration

### MQTT Auto-Discovery

Bei App-Start registrieren sich alle Sensoren automatisch in Home Assistant:

- `sensor.wetterstation_temperatur` – Außentemperatur
- `sensor.wetterstation_luftfeuchte` – Relative Luftfeuchte
- `sensor.wetterstation_wind` – Windgeschwindigkeit
- `sensor.wetterstation_luftdruck` – Barometrischer Druck
- `sensor.wetterstation_regen_heute` – Tages-Niederschlag
- `sensor.wetterstation_solar` – Solarstrahlung
- `sensor.wetterstation_uv_index` – UV-Index
- ... und viele weitere

### Webhooks

Events werden sofort an Home Assistant gemeldet:

- `weather_data` – bei jedem neuen Messwert (60s)
- `weather_alert` – bei Warnungs-Aktivierung/-Deaktivierung
- `app_start` / `app_stop` – bei Container-Start/Stop

---

## ⚙️ Installation & Konfiguration

### Docker (empfohlen)

```bash
git clone <repo-url> hc_weda
cd hc_weda
cp .env.example .env
nano .env                    # MQTT + Koordinaten setzen
make build && make up
# → Dashboard: http://localhost:5021
# → Receiver:  http://localhost:8089/weatherstation
```

### Wetterstation konfigurieren

Im WS-View Menü der Sainlogic WS3500:
- **Protocol**: Ecowitt
- **Server IP**: IP des Docker-Hosts
- **Port**: 8089
- **Path**: /weatherstation
- **Interval**: 60s

### Wichtige Umgebungsvariablen

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `MQTT_BROKER` | `10.1.1.119` | MQTT Broker IP |
| `MQTT_PORT` | `1883` | MQTT Port |
| `HA_BASETOPIC` | `hc_weda` | MQTT Basis-Topic |
| `HA_DISCOVERY` | – | HA Discovery aktivieren |
| `HA_WEBHOOK_URL` | – | Webhook URL |
| `DB_PATH` | `data/weather.db` | SQLite Dateipfad |
| `OPENWEATHER_LAT` | `47.1410` | Breite für Forecast |
| `OPENWEATHER_LON` | `9.5209` | Länge für Forecast |
| `PORT` | `5000` | App-Port intern |
| `LOG_LEVEL` | `INFO` | Log-Level |

---

## 📊 Datenbank – Über eine Million Messwerte

Die SQLite-Datenbank wächst um ca. 1.440 Einträge pro Tag (1 Messung/Minute). Seit April 2024 sind das über **eine Million Datenpunkte** – eine beeindruckende Langzeit-Datenbasis für Klimaanalysen.

```bash
make db-stats      # Anzahl, Zeitraum, Dateigröße
make db-latest     # Letzter Messwert
make db-check      # Integrität prüfen
make backup        # Backup erstellen
```

Die API bietet automatisches **Downsampling** bei großen Zeiträumen: Werden mehr als 2.000 Punkte abgefragt, wird auf ~1.000 reduziert – das Dashboard bleibt performant.

---

## 🛠️ Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| **Backend** | Python 3.12, FastAPI, Pydantic |
| **Datenbank** | SQLite (Zero-Config) |
| **Frontend** | HTML/JS/CSS (SPA) |
| **Kommunikation** | HTTP Receiver, MQTT, Webhooks |
| **Vorhersage** | Open-Meteo API (kostenlos) |
| **Deployment** | Docker Compose, Make-Workflow |
| **Code Quality** | Ruff (Linter + Formatter) |

---

## 💡 Erkenntnisse aus über einem Jahr Betrieb

Einige interessante Beobachtungen aus dem Langzeit-Archiv:

- **Temperaturspanne** am Standort: von -12°C (Januar) bis +38°C (Juli) – über 50 Grad Differenz
- **Regenreichster Monat**: typischerweise Juni/Juli mit 80–120 mm
- **Windstärkster Tag**: Böen bis 95 km/h (Beaufort 10 – "schwerer Sturm")
- **Sonnenstrahlung Peak**: über 1.100 W/m² an klaren Sommertagen um 13 Uhr
- **Gefühlte Temperatur**: kann im Winter mit Wind bis zu 10°C unter dem Messwert liegen
- **Lüftungsempfehlung**: im Sommer morgens vor 8 Uhr lüften, tagsüber Fenster zu – das System bestätigt das quantitativ

<hr style="margin-bottom: 4rem">

### Dashboard & Wetterdaten
{{< gallery >}}
  {{< image-dir >}}
{{< /gallery >}}

<hr style="margin-bottom: 4rem">

{{< notice tip >}}
  &raquo; **Migration**: Bei Update von v1 auf v2 unbedingt `make migrate` ausführen – die bestehende SQLite-DB wird übernommen, kein Datenverlust.<br>
  &raquo; **Backup**: Die SQLite-Datei `data/weather.db` enthält die gesamte Messhistorie – regelmäßig sichern!<br>
  &raquo; **Sensor-Timeout**: Wenn 15 Minuten keine Daten ankommen, meldet die App das Gerät als "nicht erreichbar" – Batterie oder WLAN prüfen.<br>
  &raquo; **Forecast-Standort**: Die Koordinaten in `OPENWEATHER_LAT`/`LON` sollten dem tatsächlichen Standort der Wetterstation entsprechen.<br>
{{< /notice >}}

