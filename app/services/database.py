# -*- coding: utf-8 -*-
"""
Database Manager
================
SQLite-Datenbank für Wetterstations-Historiendaten.
Kompatibel mit hc_weda v1 Schema.

Tabelle measurements:
    - Rohdaten (imperial): tempf, humidity, windspeedmph, rainin, baromin, etc.
    - Berechnet (metrisch): temp_c, windspeed_kmh, rain_mm, pressure_hpa, etc.
    - Primärschlüssel: dateutc (Zeitstempel)

Tabelle csv_imports:
    - Tracking für CSV-Import (verhindert Duplikate)
"""

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import DB_PATH
from app.core.logging import setup_logger

log = setup_logger("database")


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
        """Erstellt Tabellen (kompatibel mit hc_weda v1)."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS measurements (
                dateutc         TEXT PRIMARY KEY,
                device          TEXT,
                station_id      TEXT,

                -- Roh (imperial)
                indoortempf     REAL,
                tempf           REAL,
                dewptf          REAL,
                windchillf      REAL,
                indoorhumidity  INTEGER,
                humidity        INTEGER,
                windspeedmph    REAL,
                windgustmph     REAL,
                winddir         INTEGER,
                absbaromin      REAL,
                baromin         REAL,
                rainin          REAL,
                dailyrainin     REAL,
                weeklyrainin    REAL,
                monthlyrainin   REAL,
                solarradiation  REAL,
                uv              INTEGER,

                -- Berechnet (metrisch)
                indoor_temp_c   REAL,
                temp_c          REAL,
                dewpoint_c      REAL,
                windchill_c     REAL,
                windspeed_kmh   REAL,
                windgust_kmh    REAL,
                abs_pressure_hpa REAL,
                pressure_hpa    REAL,
                rain_mm         REAL,
                daily_rain_mm   REAL,
                weekly_rain_mm  REAL,
                monthly_rain_mm REAL,

                -- Zusätzliche berechnete Werte (v2)
                feels_like_c    REAL,
                wind_dir_text   TEXT,
                beaufort        INTEGER,
                beaufort_text   TEXT,
                temp_diff_c     REAL,
                climate_advice  TEXT,
                frost_text      TEXT,
                solar_klux      REAL,

                -- Meta
                softwaretype    TEXT,
                date_local      TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_dateutc ON measurements (dateutc);
            CREATE INDEX IF NOT EXISTS idx_date_local ON measurements (date_local);

            CREATE TABLE IF NOT EXISTS daily_stats (
                day             TEXT PRIMARY KEY,
                temp_min        REAL,
                temp_max        REAL,
                temp_avg        REAL,
                hum_min         REAL,
                hum_max         REAL,
                hum_avg         REAL,
                wind_max        REAL,
                gust_max        REAL,
                rain_day        REAL,
                pressure_min    REAL,
                pressure_max    REAL,
                solar_max       REAL,
                uv_max          REAL
            );

            CREATE TABLE IF NOT EXISTS csv_imports (
                filename TEXT PRIMARY KEY,
                mtime    REAL
            );
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Wetterdaten einfügen
    # ------------------------------------------------------------------
    def insert_weather_reading(self, reading) -> bool:
        """Fügt ein WeatherReading-Objekt in die DB ein.

        Args:
            reading: WeatherReading Objekt

        Returns:
            True bei Erfolg
        """
        try:
            with self._lock:
                self.conn.execute("""
                    INSERT OR REPLACE INTO measurements (
                        dateutc, device, station_id,
                        indoortempf, tempf, dewptf, windchillf,
                        indoorhumidity, humidity,
                        windspeedmph, windgustmph, winddir,
                        absbaromin, baromin,
                        rainin, dailyrainin, weeklyrainin, monthlyrainin,
                        solarradiation, uv,
                        indoor_temp_c, temp_c, dewpoint_c, windchill_c,
                        windspeed_kmh, windgust_kmh,
                        abs_pressure_hpa, pressure_hpa,
                        rain_mm, daily_rain_mm, weekly_rain_mm, monthly_rain_mm,
                        feels_like_c, wind_dir_text, beaufort, beaufort_text,
                        temp_diff_c, climate_advice, frost_text, solar_klux,
                        softwaretype, date_local
                    ) VALUES (
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?
                    )
                """, (
                    reading.timestamp,
                    "sainlogic-ws3500",
                    "ips-ws3500",
                    # Imperial
                    reading.indoor_temp_c * 9/5 + 32 if reading.indoor_temp_c else None,
                    reading.temp_f,
                    reading.dewpoint_c * 9/5 + 32 if reading.dewpoint_c else None,
                    reading.windchill_c * 9/5 + 32 if reading.windchill_c else None,
                    reading.indoor_humidity,
                    reading.humidity,
                    reading.wind_speed_mph,
                    reading.wind_gust_kmh / 1.60934 if reading.wind_gust_kmh else None,
                    reading.wind_dir_deg,
                    reading.abs_pressure_hpa / 33.8639 if reading.abs_pressure_hpa else None,
                    reading.pressure_inhg,
                    reading.rain_rate_mmh / 25.4 if reading.rain_rate_mmh else None,
                    reading.rain_daily_mm / 25.4 if reading.rain_daily_mm else None,
                    reading.rain_weekly_mm / 25.4 if reading.rain_weekly_mm else None,
                    reading.rain_monthly_mm / 25.4 if reading.rain_monthly_mm else None,
                    reading.solar_radiation,
                    reading.uv_index,
                    # Metrisch
                    reading.indoor_temp_c,
                    reading.temp_c,
                    reading.dewpoint_c,
                    reading.windchill_c,
                    reading.wind_speed_kmh,
                    reading.wind_gust_kmh,
                    reading.abs_pressure_hpa,
                    reading.pressure_hpa,
                    reading.rain_rate_mmh,
                    reading.rain_daily_mm,
                    reading.rain_weekly_mm,
                    reading.rain_monthly_mm,
                    # Zusätzlich (v2)
                    reading.feels_like_c,
                    reading.wind_dir_text,
                    reading.beaufort,
                    reading.beaufort_text,
                    reading.temp_diff_c,
                    reading.climate_advice,
                    reading.frost_text,
                    reading.solar_klux,
                    # Meta
                    "hc_weda_v2",
                    reading.date,
                ))
                self.conn.commit()
            return True
        except Exception as e:
            log.error("Fehler beim Einfügen in DB: %s", e)
            return False

    # ------------------------------------------------------------------
    # Abfragen (für Dashboard/API)
    # ------------------------------------------------------------------
    def get_latest_reading(self) -> Optional[dict]:
        """Letzter Messwert."""
        row = self.conn.execute(
            "SELECT * FROM measurements ORDER BY dateutc DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_readings_for_date(self, date: str) -> list[dict]:
        """Alle Messwerte für einen Tag."""
        rows = self.conn.execute("""
            SELECT * FROM measurements
            WHERE date_local = ?
            ORDER BY dateutc
        """, (date,)).fetchall()
        return [dict(r) for r in rows]

    def get_daily_summary(self, date: str) -> Optional[dict]:
        """Tageszusammenfassung (Min/Max/Avg)."""
        row = self.conn.execute("""
            SELECT
                COUNT(*) as count,
                MIN(temp_c) as temp_min,
                MAX(temp_c) as temp_max,
                AVG(temp_c) as temp_avg,
                MIN(humidity) as humidity_min,
                MAX(humidity) as humidity_max,
                AVG(humidity) as humidity_avg,
                MAX(windgust_kmh) as wind_max,
                MAX(daily_rain_mm) as rain_total,
                AVG(pressure_hpa) as pressure_avg
            FROM measurements
            WHERE date_local = ?
        """, (date,)).fetchone()
        return dict(row) if row and row["count"] else None

    def get_date_range(self, from_date: str, to_date: str) -> list[dict]:
        """Messwerte in einem Zeitraum."""
        rows = self.conn.execute("""
            SELECT * FROM measurements
            WHERE date_local BETWEEN ? AND ?
            ORDER BY dateutc
        """, (from_date, to_date)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Statistiken über die Datenbank."""
        r = self.conn.execute("SELECT COUNT(*) as cnt FROM measurements").fetchone()
        first = self.conn.execute("SELECT MIN(dateutc) as first FROM measurements").fetchone()
        last = self.conn.execute("SELECT MAX(dateutc) as last FROM measurements").fetchone()
        return {
            "measurements": r["cnt"],
            "first_reading": first["first"] if first else None,
            "last_reading": last["last"] if last else None,
        }

    # ------------------------------------------------------------------
    # Tages-Aggregation (Cache)
    # ------------------------------------------------------------------
    def rebuild_daily_stats(self):
        """Befüllt daily_stats für alle Tage, die noch fehlen (außer heute)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            self.conn.execute("""
                INSERT OR IGNORE INTO daily_stats (day, temp_min, temp_max, temp_avg,
                    hum_min, hum_max, hum_avg, wind_max, gust_max, rain_day,
                    pressure_min, pressure_max, solar_max, uv_max)
                SELECT
                    substr(dateutc, 1, 10) AS day,
                    ROUND(MIN(temp_c), 1),
                    ROUND(MAX(temp_c), 1),
                    ROUND(AVG(temp_c), 1),
                    ROUND(MIN(humidity), 0),
                    ROUND(MAX(humidity), 0),
                    ROUND(AVG(humidity), 0),
                    ROUND(MAX(windspeed_kmh), 1),
                    ROUND(MAX(windgust_kmh), 1),
                    ROUND(MAX(daily_rain_mm), 2),
                    ROUND(MIN(pressure_hpa), 1),
                    ROUND(MAX(pressure_hpa), 1),
                    ROUND(MAX(solarradiation), 1),
                    ROUND(MAX(uv), 0)
                FROM measurements
                WHERE temp_c IS NOT NULL
                  AND substr(dateutc, 1, 10) < ?
                  AND substr(dateutc, 1, 10) NOT IN (SELECT day FROM daily_stats)
                GROUP BY day
            """, (today,))
            inserted = self.conn.total_changes
            self.conn.commit()
        log.info("daily_stats aktualisiert (%d neue Tage)", inserted)

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
