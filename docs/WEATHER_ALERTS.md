# Wetter-Warnungen

Das Wetter-Warnsystem überwacht kontinuierlich die Wetterdaten und sendet automatisch Webhooks an Home Assistant, wenn bestimmte Schwellwerte überschritten werden.

## Warnungstypen

### 1. Sturm-Warnung (`storm`)
**Aktiviert wenn:**
- Windgeschwindigkeit > 50 km/h **ODER**
- Böen > 70 km/h

**Webhook-Payload:**
```json
{
  "event": "weather_alert",
  "alert_type": "storm",
  "state": "on",
  "message": "Sturm! Wind: 55.2 km/h, Böen: 75.3 km/h",
  "severity": "warning",
  "wind_kmh": 55.2,
  "gust_kmh": 75.3,
  "timestamp": "2026-05-09T14:30:00"
}
```

### 2. Starkregen-Warnung (`heavy_rain`)
**Aktiviert wenn:**
- Regenrate > 10 mm/h

**Webhook-Payload:**
```json
{
  "event": "weather_alert",
  "alert_type": "heavy_rain",
  "state": "on",
  "message": "Starkregen! 12.5 mm/h",
  "severity": "warning",
  "rain_rate_mmh": 12.5,
  "timestamp": "2026-05-09T14:30:00"
}
```

### 3. Frost-Warnung (`frost`)
**Aktiviert wenn:**
- Temperatur ≤ 0°C

**Webhook-Payload:**
```json
{
  "event": "weather_alert",
  "alert_type": "frost",
  "state": "on",
  "message": "Frost! Temperatur: -2.1°C",
  "severity": "warning",
  "temp_c": -2.1,
  "timestamp": "2026-05-09T14:30:00"
}
```

### 4. Frostgefahr-Warnung (`freeze_risk`)
**Aktiviert wenn:**
- Temperatur > 0°C **UND** ≤ 3°C

**Webhook-Payload:**
```json
{
  "event": "weather_alert",
  "alert_type": "freeze_risk",
  "state": "on",
  "message": "Frostgefahr! Temperatur: 2.3°C",
  "severity": "info",
  "temp_c": 2.3,
  "timestamp": "2026-05-09T14:30:00"
}
```

## Hysterese & Cooldown

Um "Flapping" (ständiges An/Aus) zu verhindern, verwendet das System:

### Mindestdauer (Hysterese)
- Warnung bleibt **mindestens 15 Minuten** aktiv
- Auch wenn Schwellwert kurzzeitig unterschritten wird
- Verhindert Spam bei schwankenden Werten

### Cooldown
- Nach Deaktivierung: **5 Minuten Pause**
- Keine neue Warnung in dieser Zeit
- Verhindert sofortige Reaktivierung

## Konfiguration

Schwellwerte in `.env` anpassen:

```bash
# Sturm-Warnung
ALERT_STORM_WIND=50.0          # km/h - Windgeschwindigkeit
ALERT_STORM_GUST=70.0          # km/h - Böen

# Regen-Warnung
ALERT_HEAVY_RAIN=10.0          # mm/h - Regenrate

# Frost-Warnungen
ALERT_FROST=0.0                # °C - Frost (≤ 0°C)
ALERT_FREEZE_RISK=3.0          # °C - Frostgefahr (≤ 3°C)

# Hysterese
ALERT_MIN_DURATION=15          # Minuten
ALERT_COOLDOWN=5               # Minuten
```

## Home Assistant Integration

### Webhook-Automation Beispiel

```yaml
automation:
  - alias: "Wetter: Sturm-Warnung"
    trigger:
      - platform: webhook
        webhook_id: hc_weda
    condition:
      - condition: template
        value_template: "{{ trigger.json.event == 'weather_alert' }}"
      - condition: template
        value_template: "{{ trigger.json.alert_type == 'storm' }}"
      - condition: template
        value_template: "{{ trigger.json.state == 'on' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Sturm-Warnung"
          message: "{{ trigger.json.message }}"
          data:
            priority: high
            ttl: 0

  - alias: "Wetter: Frost-Warnung"
    trigger:
      - platform: webhook
        webhook_id: hc_weda
    condition:
      - condition: template
        value_template: "{{ trigger.json.event == 'weather_alert' }}"
      - condition: template
        value_template: "{{ trigger.json.alert_type == 'frost' }}"
      - condition: template
        value_template: "{{ trigger.json.state == 'on' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "❄️ Frost-Warnung"
          message: "{{ trigger.json.message }}"
```

### Binary Sensor für aktive Warnungen

```yaml
template:
  - binary_sensor:
      - name: "Wetter Sturm-Warnung"
        unique_id: weather_alert_storm
        state: "{{ states('sensor.hc_weda_alert_storm') == 'on' }}"
        device_class: safety

      - name: "Wetter Frost-Warnung"
        unique_id: weather_alert_frost
        state: "{{ states('sensor.hc_weda_alert_frost') == 'on' }}"
        device_class: cold
```

## Webhook-Endpunkt

**URL:** `http://10.1.1.217:8123/api/webhook/hc_weda`

Alle Warnungen werden an diesen Endpunkt gesendet. Home Assistant kann dann mit Automationen darauf reagieren.

## Logs

Warnungen werden geloggt:

```
2026-05-09 14:30:00 [INFO] weather_alerts: Warnung aktiviert: storm
2026-05-09 14:45:00 [INFO] weather_alerts: Warnung deaktiviert: storm
```

## Deaktivierung

Um Warnungen zu deaktivieren, setze die Schwellwerte sehr hoch:

```bash
ALERT_STORM_WIND=999.0
ALERT_STORM_GUST=999.0
ALERT_HEAVY_RAIN=999.0
```

Oder kommentiere die Warnung im Code aus (`weather_alerts.py`).
