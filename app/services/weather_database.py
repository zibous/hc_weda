# -*- coding: utf-8 -*-
"""
Weather Database Manager
========================
SQLite-Datenbank für Wetterstations-Historiendaten.

Tabelle weather_readings:
    - Alle Wetterdaten (Temperatur, Wind, Regen, Druck, Solar, UV)
    - Metrische Einheiten (Celsius, mm, km/h, hPa)

Tabelle daily_weather_summary:
    - Tageswerte (Min/Max/Durchschnitt)
"""

import csv
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import DB_PATH
from app.core.logging import setup_logger
from app.models.weather import WeatherReading

log = setup_logger("weather_database")


class WeatherDB:
    """SQLite-Datenbank für Wetterdaten."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._lock = threading.Lock()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=30,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=10000")
        self._create_tables()
        log.info("WeatherDB initialisiert: %s", self.db_path)

    def _create_tables(self):
        """Erstellt Tabellen für Wetterdaten."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS weather_readings (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp           TEXT NOT NULL,
                date                TEXT NOT NULL,
                time                TEXT,
                
                -- Temperatur (°C)
                temp_c              REAL,
                temp_f              REAL,
                feels_like_c        REAL,
                indoor_temp_c       REAL,
                dewpoint_c          REAL,
                windchill_c         REAL,
                
                -- Luftfeuchte (%)
                humidity            INTEGER,
                indoor_humidity     INTEGER,
                
                -- Wind
                wind_speed_kmh      REAL,
                wind_speed_mph      REAL,
                wind_gust_kmh       REAL,
                wind_dir_deg        INTEGER,
                wind_dir_text       TEXT,
                beaufort            INTEGER,
                beaufort_text       TEXT,
                
                -- Regen (mm)
                rain_rate_mmh       REAL,
                rain_daily_mm       REAL,
                rain_weekly_mm      REAL,
                rain_monthly_mm     REAL,
                
                -- Luftdruck (hPa)
                pressure_hpa        REAL,
                pressure_inhg       REAL,
                abs_pressure_hpa    REAL,
                
                -- Solar / UV
                solar_radiation     REAL,
                solar_klux          REAL,
                uv_index            INTEGER,
                
                -- Raumklima
                temp_diff_c         REAL,
                climate_advice      TEXT,
                frost_text          TEXT,
                
                -- Quelle
                source              TEXT DEFAULT 'sainlogic-ws3500',
                
                UNIQUE(date, time)
            );
            
            CREATE INDEX IF NOT EXISTS idx_weather_date ON weather_readings(date);
            CREATE INDEX IF NOT EXISTS idx_weather_ts ON weather_readings(timestamp);

            CREATE TABLE IF NOT EXISTS daily_weather_summary (
                date                TEXT PRIMARY KEY,
                
                -- Temperatur (Min/Max/Avg)
                temp_min_c          REAL,
                temp_max_c          REAL,
                temp_avg_c          REAL,
                feels_like_min_c    REAL,
                feels_like_max_c    REAL,
                
                -- Wind (Max)
                wind_max_kmh        REAL,
                wind_gust_max_kmh   REAL,
                
                -- Regen (Summe)
                rain_total_mm       REAL,
                
                -- Luftdruck (Min/Max/Avg)
                pressure_min_hpa    REAL,
                pressure_max_hpa    REAL,
                pressure_avg_hpa    REAL,
                
                -- Solar / UV (Max)
                solar_max_wm2       REAL,
                uv_max              INTEGER,
                
                -- Statistik
                readings_count      INTEGER DEFAULT 0,
                last_update         TEXT
            );
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Readings einfügen
    # ------------------------------------------------------------------
    def insert_weather_reading(self, reading: WeatherReading) -> int:
        """Fügt ein WeatherReading-Objekt in die DB ein."""
        with self._lock:
            cur = self.conn.execute("""
                INSERT OR REPLACE INTO weather_readings (
                    timestamp, date, time,
                    temp_c, temp_f, feels_like_c, indoor_temp_c, dewpoint_c, windchill_c,
                    humidity, indoor_humidity,
                    wind_speed_kmh, wind_speed_mph, wind_gust_kmh,
                    wind_dir_deg, wind_dir_text, beaufort, beaufort_text,
                    rain_rate_mmh, rain_daily_mm, rain_weekly_mm, rain_monthly_mm,
                    pressure_hpa, pressure_inhg, abs_pressure_hpa,
                    solar_radiation, solar_klux, uv_index,
                    temp_diff_c, climate_advice, frost_text,
                    source
                ) VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?
                )
            """, (
                reading.timestamp, reading.date, reading.time,
                reading.temp_c, reading.temp_f, reading.feels_like_c,
                reading.indoor_temp_c, reading.dewpoint_c, reading.windchill_c,
                reading.humidity, reading.indoor_humidity,
                reading.wind_speed_kmh, reading.wind_speed_mph, reading.wind_gust_kmh,
                reading.wind_dir_deg, reading.wind_dir_text, reading.beaufort, reading.beaufort_text,
                reading.rain_rate_mmh, reading.rain_daily_mm, reading.rain_weekly_mm, reading.rain_monthly_mm,
                reading.pressure_hpa, reading.pressure_inhg, reading.abs_pressure_hpa,
                reading.solar_radiation, reading.solar_klux, reading.uv_index,
                reading.temp_diff_c, reading.climate_advice, reading.frost_text,
                reading.source
            ))
            self.conn.commit()
        return cur.lastrowid or 0

    # ------------------------------------------------------------------
    # Tages-Summary berechnen
    # ------------------------------------------------------------------
    def update_daily_summary(self, date: str):
        """Berechnet Tageswerte (Min/Max/Avg) aus Messwerten."""
        with self._lock:
            row = self.conn.execute("""
                SELECT
                    MIN(temp_c) as temp_min,
                    MAX(temp_c) as temp_max,
                    AVG(temp_c) as temp_avg,
                    MIN(feels_like_c) as feels_min,
                    MAX(feels_like_c) as feels_max,
                    MAX(wind_speed_kmh) as wind_max,
                    MAX(wind_gust_kmh) as gust_max,
                    MAX(rain_daily_mm) as rain_total,
                    MIN(pressure_hpa) as pressure_min,
                    MAX(pressure_hpa) as pressure_max,
                    AVG(pressure_hpa) as pressure_avg,
                    MAX(solar_radiation) as solar_max,
                    MAX(uv_index) as uv_max,
                    COUNT(*) as cnt
                FROM weather_readings
                WHERE date = ?
            """, (date,)).fetchone()

            if not row or row["cnt"] == 0:
                return

            now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

            self.conn.execute("""
                INSERT INTO daily_weather_summary (
                    date,
                    temp_min_c, temp_max_c, temp_avg_c,
                    feels_like_min_c, feels_like_max_c,
                    wind_max_kmh, wind_gust_max_kmh,
                    rain_total_mm,
                    pressure_min_hpa, pressure_max_hpa, pressure_avg_hpa,
                    solar_max_wm2, uv_max,
                    readings_count, last_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    temp_min_c=excluded.temp_min_c,
                    temp_max_c=excluded.temp_max_c,
                    temp_avg_c=excluded.temp_avg_c,
                    feels_like_min_c=excluded.feels_like_min_c,
                    feels_like_max_c=excluded.feels_like_max_c,
                    wind_max_kmh=excluded.wind_max_kmh,
                    wind_gust_max_kmh=excluded.wind_gust_max_kmh,
                    rain_total_mm=excluded.rain_total_mm,
                    pressure_min_hpa=excluded.pressure_min_hpa,
                    pressure_max_hpa=excluded.pressure_max_hpa,
                    pressure_avg_hpa=excluded.pressure_avg_hpa,
                    solar_max_wm2=excluded.solar_max_wm2,
                    uv_max=excluded.uv_max,
                    readings_count=excluded.readings_count,
                    last_update=excluded.last_update
            """, (
                date,
                row["temp_min"], row["temp_max"], row["temp_avg"],
                row["feels_min"], row["feels_max"],
                row["wind_max"], row["gust_max"],
                row["rain_total"],
                row["pressure_min"], row["pressure_max"], row["pressure_avg"],
                row["solar_max"], row["uv_max"],
                row["cnt"], now_utc
            ))
            self.conn.commit()

    # ------------------------------------------------------------------
    # CSV-Import
    # ------------------------------------------------------------------
    def import_csv(self, csv_path: str) -> tuple[int, int]:
        """Importiert eine CSV-Datei. Returns (imported, skipped)."""
        imported = skipped = 0
        dates_seen: set[str] = set()

        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                with self._lock:
                    for row in reader:
                        date = row.get("date", "").strip()
                        time_val = row.get("time", "").strip()
                        if not date:
                            skipped += 1
                            continue

                        # WeatherReading aus CSV erstellen
                        try:
                            reading = WeatherReading(
                                timestamp=f"{date} {time_val}" if time_val else date,
                                date=date,
                                time=time_val,
                                temp_c=float(row.get("temp_c", 0) or 0) or None,
                                humidity=int(row.get("humidity", 0) or 0) or None,
                                wind_speed_kmh=float(row.get("wind_speed_kmh", 0) or 0) or None,
                                pressure_hpa=float(row.get("pressure_hpa", 0) or 0) or None,
                                # ... weitere Felder nach Bedarf
                            )
                            self.insert_weather_reading(reading)
                            imported += 1
                            dates_seen.add(date)
                        except (ValueError, TypeError):
                            skipped += 1
                            continue

                    self.conn.commit()

            # Tages-Summaries aktualisieren
            for d in sorted(dates_seen):
                self.update_daily_summary(d)

        except Exception:
            log.exception("CSV-Import fehlgeschlagen: %s", csv_path)

        return imported, skipped

    # ------------------------------------------------------------------
    # Abfragen (für Dashboard/API)
    # ------------------------------------------------------------------
    def get_latest_reading(self) -> Optional[dict]:
        """Letzter Messwert."""
        row = self.conn.execute(
            "SELECT * FROM weather_readings ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_daily_summary(self, date: str) -> Optional[dict]:
        """Tageszusammenfassung."""
        row = self.conn.execute(
            "SELECT * FROM daily_weather_summary WHERE date=?", (date,)
        ).fetchone()
        return dict(row) if row else None

    def get_daily_range(self, from_date: str, to_date: str) -> list[dict]:
        """Tageswerte in einem Zeitraum."""
        rows = self.conn.execute("""
            SELECT * FROM daily_weather_summary
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """, (from_date, to_date)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Statistiken über die Datenbank."""
        r = self.conn.execute("SELECT COUNT(*) as cnt FROM weather_readings").fetchone()
        d = self.conn.execute("SELECT COUNT(*) as cnt FROM daily_weather_summary").fetchone()
        return {"readings": r["cnt"], "days": d["cnt"]}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self):
        """Schliesst die Datenbankverbindung."""
        if self.conn:
            self.conn.close()
            log.info("WeatherDB geschlossen")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ------------------------------------------------------------------
# Kompatibilitätsfunktion (für main.py lifespan)
# ------------------------------------------------------------------
_db_instance: Optional[WeatherDB] = None


def init_db(db_path: Optional[str] = None) -> WeatherDB:
    """Initialisiert die globale DB-Instanz."""
    global _db_instance
    _db_instance = WeatherDB(db_path)
    return _db_instance


def get_db() -> WeatherDB:
    """Gibt die globale DB-Instanz zurück."""
    if _db_instance is None:
        raise RuntimeError("Datenbank nicht initialisiert. init_db() aufrufen.")
    return _db_instance
