#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Script: hc_weda v1 → v2
==================================
Kopiert alle Wetterdaten von v1 (history.db) nach v2 (weather.db).

WICHTIG:
- v1 Datenbank bleibt unverändert (Read-Only)
- v2 Datenbank wird erstellt/erweitert
- Duplikate werden übersprungen (INSERT OR REPLACE)

Usage:
    python scripts/migrate_v1_to_v2.py
    python scripts/migrate_v1_to_v2.py --v1-db /path/to/history.db --v2-db /path/to/weather.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Standardpfade
DEFAULT_V1_DB = "/dockerapps/apps_v1/hc_weda/data/history.db"
DEFAULT_V2_DB = "/dockerapps/apps_v2/hc_weda/data/weather.db"


def migrate_data(v1_db_path: str, v2_db_path: str, batch_size: int = 10000):
    """Migriert Daten von v1 nach v2.

    Args:
        v1_db_path: Pfad zur v1 Datenbank (history.db)
        v2_db_path: Pfad zur v2 Datenbank (weather.db)
        batch_size: Anzahl Zeilen pro Batch
    """
    print(f"Migration: v1 → v2")
    print(f"  v1: {v1_db_path}")
    print(f"  v2: {v2_db_path}")
    print()

    # v1 DB öffnen (Read-Only)
    if not Path(v1_db_path).exists():
        print(f"❌ v1 Datenbank nicht gefunden: {v1_db_path}")
        sys.exit(1)

    v1_conn = sqlite3.connect(f"file:{v1_db_path}?mode=ro", uri=True)
    v1_conn.row_factory = sqlite3.Row

    # v2 DB öffnen (Read-Write, erstellen falls nicht vorhanden)
    Path(v2_db_path).parent.mkdir(parents=True, exist_ok=True)
    v2_conn = sqlite3.connect(v2_db_path)
    v2_conn.execute("PRAGMA journal_mode=WAL")

    # v2 Schema erstellen (falls noch nicht vorhanden)
    _create_v2_schema(v2_conn)

    # Statistiken
    v1_count = v1_conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    v2_count_before = v2_conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]

    print(f"📊 v1 Datenbank: {v1_count:,} Messungen")
    print(f"📊 v2 Datenbank: {v2_count_before:,} Messungen (vor Migration)")
    print()

    if v1_count == 0:
        print("⚠️  Keine Daten in v1 vorhanden")
        return

    # Migration in Batches
    print(f"🔄 Starte Migration (Batch-Größe: {batch_size:,})...")
    offset = 0
    total_migrated = 0
    total_skipped = 0

    while True:
        # Batch aus v1 lesen
        rows = v1_conn.execute(f"""
            SELECT * FROM measurements
            ORDER BY dateutc
            LIMIT {batch_size} OFFSET {offset}
        """).fetchall()

        if not rows:
            break

        # Batch in v2 schreiben
        migrated, skipped = _insert_batch(v2_conn, rows)
        total_migrated += migrated
        total_skipped += skipped

        offset += len(rows)
        progress = (offset / v1_count) * 100
        print(f"  {offset:,} / {v1_count:,} ({progress:.1f}%) - "
              f"Migriert: {total_migrated:,}, Übersprungen: {total_skipped:,}")

    # Finale Statistiken
    v2_count_after = v2_conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    new_records = v2_count_after - v2_count_before

    print()
    print("✅ Migration abgeschlossen!")
    print(f"  Neue Datensätze: {new_records:,}")
    print(f"  v2 Datenbank: {v2_count_after:,} Messungen (nach Migration)")
    print()

    # Zeitraum anzeigen
    first = v2_conn.execute("SELECT MIN(dateutc) FROM measurements").fetchone()[0]
    last = v2_conn.execute("SELECT MAX(dateutc) FROM measurements").fetchone()[0]
    print(f"  Zeitraum: {first} bis {last}")

    v1_conn.close()
    v2_conn.close()


def _create_v2_schema(conn: sqlite3.Connection):
    """Erstellt v2 Schema (falls noch nicht vorhanden)."""
    conn.executescript("""
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

        CREATE TABLE IF NOT EXISTS csv_imports (
            filename TEXT PRIMARY KEY,
            mtime    REAL
        );
    """)
    conn.commit()


def _insert_batch(conn: sqlite3.Connection, rows: list) -> tuple[int, int]:
    """Fügt einen Batch in v2 ein.

    Returns:
        (migrated, skipped)
    """
    migrated = 0
    skipped = 0

    for row in rows:
        try:
            conn.execute("""
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
                    ?, ?
                )
            """, (
                row["dateutc"], row["device"], row["station_id"],
                row["indoortempf"], row["tempf"], row["dewptf"], row["windchillf"],
                row["indoorhumidity"], row["humidity"],
                row["windspeedmph"], row["windgustmph"], row["winddir"],
                row["absbaromin"], row["baromin"],
                row["rainin"], row["dailyrainin"], row["weeklyrainin"], row["monthlyrainin"],
                row["solarradiation"], row["uv"],
                row["indoor_temp_c"], row["temp_c"], row["dewpoint_c"], row["windchill_c"],
                row["windspeed_kmh"], row["windgust_kmh"],
                row["abs_pressure_hpa"], row["pressure_hpa"],
                row["rain_mm"], row["daily_rain_mm"], row["weekly_rain_mm"], row["monthly_rain_mm"],
                row["softwaretype"], row["date_local"],
            ))
            migrated += 1
        except sqlite3.IntegrityError:
            # Duplikat (sollte nicht vorkommen bei INSERT OR REPLACE)
            skipped += 1
        except Exception as e:
            print(f"⚠️  Fehler bei Zeile {row['dateutc']}: {e}")
            skipped += 1

    conn.commit()
    return migrated, skipped


def main():
    parser = argparse.ArgumentParser(description="Migriert hc_weda v1 → v2 Datenbank")
    parser.add_argument("--v1-db", default=DEFAULT_V1_DB, help="Pfad zur v1 Datenbank")
    parser.add_argument("--v2-db", default=DEFAULT_V2_DB, help="Pfad zur v2 Datenbank")
    parser.add_argument("--batch-size", type=int, default=10000, help="Batch-Größe")
    args = parser.parse_args()

    migrate_data(args.v1_db, args.v2_db, args.batch_size)


if __name__ == "__main__":
    main()
