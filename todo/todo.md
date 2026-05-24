# p1 Meters

Das neue Gerät p1 meters hat mehr Informationen, nur so eine Iddensammlung was möglich wäre:

1. HTTP → Backup / Initial State

2. WSS → Live Daten


## Überlegung:

    Methode	Traffic/Tag	Last
    HTTP (1s polling)	~300–400 MB	hoch
    WSS	~10–50 MB	niedrig

## wss://
```python
    import asyncio
    import websockets

    async def listen():
        url = "wss://192.168.1.50/api/v2/ws"
        async with websockets.connect(url, ssl=False) as ws:
            # je nach API ggf. subscribe message senden
            await ws.send('{"type":"subscribe","topic":"measurement"}')
            while True:
                msg = await ws.recv()
                print(msg)

    asyncio.run(listen())

````

```yaml
  publish_fields:
    device_id: geraete_id
    device_name: geraete_name
    timestamp: zeitstempel
    date: datum
    time: uhrzeit
    source: quelle
    bezug: gesamt_bezug_kwh
    einspeisung: gesamt_einspeisung_kwh
    power_w: leistung_w
    power_l1_w: leistung_l1_w
    power_l2_w: leistung_l2_w
    power_l3_w: leistung_l3_w
    voltage_l1_v: spannung_l1_v
    voltage_l2_v: spannung_l2_v
    voltage_l3_v: spannung_l3_v
    frequency_hz: frequenz_hz
```

## Phasenungleichgewicht
## Wirkleistung pro Phase
## Energie (über Zeit)

```python
from datetime import datetime, date

class SmartMeter:
    def __init__(self):
        self.total_kwh = 0.0
        self.daily_kwh = 0.0
        self.last_power = None
        self.last_day = date.today()

    def _reset_if_new_day(self):
        today = date.today()
        if today != self.last_day:
            self.daily_kwh = 0.0
            self.last_day = today

    def phase_unbalance(power_l1, power_l2, power_l3):
        """
        | Wert      | Bedeutung                                |
        | --------- | ---------------------------------------- |
        | 0.0 – 0.2 | 👍 sehr gut verteilt                     |
        | 0.2 – 0.5 | ⚠️ leicht ungleich                       |
        | > 0.5     | 🚨 stark unausgeglichen                  |
        | > 1.0     | 🔥 kritisch (eine Phase dominiert stark) |
        """

        values = [power_l1, power_l2, power_l3]
        avg = sum(values) / 3
        if avg == 0:
            return 0.0
        unbalance = (max(values) - min(values)) / avg
        return round(unbalance, 3)

    import math

    def apparent_power(power_w, voltage=230):
        return power_w / voltage

    def phase_alert(power_l1, power_l2, power_l3):
        values = [power_l1, power_l2, power_l3]
        max_phase = max(values)
        avg = sum(values) / 3

        if max_phase > 2 * avg:
            return "🚨 starke Schieflast"
        elif max_phase > 1.5 * avg:
            return "⚠️ ungleich verteilt"
        else:
            return "🟢 ok"

    def phase_symmetry(power_l1, power_l2, power_l3):
        values = [power_l1, power_l2, power_l3]
        avg = sum(values) / 3
        if avg == 0:
            return 0.0
        variance = sum((v - avg) ** 2 for v in values) / 3
        std = math.sqrt(variance)

        return round(std / avg, 3)  # normierte Streuung    

    def neutral_risk(power_l1, power_l2, power_l3):
        avg = (power_l1 + power_l2 + power_l3) / 3
        imbalance = sum(abs(p - avg) for p in [power_l1, power_l2, power_l3])

        return round(imbalance / 1000, 3)  # nur Indikator

    def grid_score(l1, l2, l3):
        """
        90–100 → sehr gut
        70–90 → ok
        <70 → problematisch
        """
        avg = (l1 + l2 + l3) / 3
        symmetry = phase_symmetry(l1, l2, l3)

        score = 100 - (symmetry * 100)

        return max(0, round(score, 1))

    def update(self, power_w, interval_seconds=300):
        """
        power_w: aktuelle Gesamtleistung (HomeWizard power_w)
        interval_seconds: 300 = 5 Minuten
        """

        self._reset_if_new_day()

        if self.last_power is None:
            self.last_power = power_w
            return self.get_values()

        # Trapezregel (genauer als einfache Multiplikation)
        avg_power = (self.last_power + power_w) / 2

        energy_kwh = (avg_power * interval_seconds) / 3_600_000

        self.total_kwh += energy_kwh
        self.daily_kwh += energy_kwh

        self.last_power = power_w

        return self.get_values()

    def get_values(self):
        return {
            "total_kwh": round(self.total_kwh, 4),
            "daily_kwh": round(self.daily_kwh, 4),
            "last_power_w": self.last_power
        }
```