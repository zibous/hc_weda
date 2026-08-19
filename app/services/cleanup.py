# -*- coding: utf-8 -*-
"""
Cleanup Service
===============
Nächtlicher Job der alte Rohdaten archiviert und die Haupt-DB schlank hält.

Ablauf (täglich um 02:00):
1. daily_stats für alle fehlenden Tage aktualisieren
2. Daten älter als 90 Tage → Jahres-Archiv-DB (data/history-YYYY.db)
3. Archivierte Rohdaten aus measurements löschen
4. VACUUM bei Bedarf

Archiv-Schema: identisch mit measurements (1:1 Kopie).
Tagesaggregate (daily_stats) bleiben IMMER in der Haupt-DB.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

from app.core.config import PATHS
from app.core.logging import setup_logger

log = setup_logger("cleanup")

RETENTION_DAYS = 90
ARCHIVE_DIR = PATHS["data"]


def _cutoff_date() -> str:
    """Berechnet das Datum ab dem archiviert wird (heute - 90 Tage)."""
    return (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")


def _get_years_to_archive(conn: sqlite3.Connection, cutoff: str) -> list[str]:
    """Ermittelt welche Jahre archiviert werden müssen."""
    rows = conn.execute(
        "SELECT DISTINCT substr(dateutc, 1, 4) AS year FROM measurements WHERE dateutc < ? ORDER BY year",
        (f"{cutoff} 00:00:00",)
    ).fetchall()
    return [r["year"] for r in rows]


def _ensure_archive_db(year: str) -> sqlite3.Connection:
    """Erstellt/öffnet die Archiv-DB für ein Jahr."""
    path = ARCHIVE_DIR / f"history-{year}.db"
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            dateutc         TEXT PRIMARY KEY,
            device          TEXT,
            station_id      TEXT,
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
            feels_like_c    REAL,
            wind_dir_text   TEXT,
            beaufort        INTEGER,
            beaufort_text   TEXT,
            temp_diff_c     REAL,
            climate_advice  TEXT,
            frost_text      TEXT,
            solar_klux      REAL,
            softwaretype    TEXT,
            date_local      TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dateutc ON measurements (dateutc)")
    conn.commit()
    return conn


def run_cleanup(db) -> dict:
    """Führt den kompletten Cleanup-Zyklus durch.

    Args:
        db: WeatherDB-Instanz

    Returns:
        dict mit Statistiken (archived, deleted, daily_stats_added)
    """
    stats = {"archived": 0, "deleted": 0, "years": []}
    cutoff = _cutoff_date()
    log.info("Cleanup gestartet (cutoff: %s, Retention: %d Tage)", cutoff, RETENTION_DAYS)

    # 1. daily_stats aktualisieren (sicherstellen dass nichts verloren geht)
    db.rebuild_daily_stats()

    # 2. Archivierung pro Jahr
    years = _get_years_to_archive(db.conn, cutoff)
    if not years:
        log.info("Keine Daten zum Archivieren")
        return stats

    for year in years:
        year_start = f"{year}-01-01 00:00:00"
        year_end = f"{year}-12-31 23:59:59"
        # Nur Daten vor dem Cutoff archivieren
        archive_end = min(f"{cutoff} 00:00:00", year_end)

        # Zählen was zu archivieren ist
        count_row = db.conn.execute(
            "SELECT COUNT(*) AS cnt FROM measurements WHERE dateutc >= ? AND dateutc < ?",
            (year_start, archive_end)
        ).fetchone()
        count = count_row["cnt"] if count_row else 0

        if count == 0:
            continue

        log.info("Archiviere %d Zeilen für Jahr %s", count, year)

        # Archiv-DB öffnen
        archive_conn = _ensure_archive_db(year)

        try:
            # Batch-weise archivieren (10.000 pro Batch)
            batch_size = 10_000
            archived_year = 0

            while True:
                rows = db.conn.execute(
                    "SELECT * FROM measurements WHERE dateutc >= ? AND dateutc < ? ORDER BY dateutc LIMIT ?",
                    (year_start, archive_end, batch_size)
                ).fetchall()

                if not rows:
                    break

                # In Archiv einfügen
                cols = rows[0].keys()
                placeholders = ",".join(["?"] * len(cols))
                archive_conn.executemany(
                    f"INSERT OR IGNORE INTO measurements ({','.join(cols)}) VALUES ({placeholders})",
                    [tuple(r) for r in rows]
                )
                archive_conn.commit()

                # Aus Haupt-DB löschen
                last_ts = rows[-1]["dateutc"]
                first_ts = rows[0]["dateutc"]
                db.conn.execute(
                    "DELETE FROM measurements WHERE dateutc >= ? AND dateutc <= ?",
                    (first_ts, last_ts)
                )
                db.conn.commit()

                archived_year += len(rows)

                if len(rows) < batch_size:
                    break

            stats["archived"] += archived_year
            stats["deleted"] += archived_year
            stats["years"].append(year)
            log.info("Jahr %s: %d Zeilen archiviert → history-%s.db", year, archived_year, year)

        finally:
            archive_conn.close()

    # 3. Verbleibende alte Daten löschen (z.B. laufendes Jahr, aber vor 90 Tagen)
    current_year = datetime.now(timezone.utc).strftime("%Y")
    if cutoff[:4] == current_year:
        # Daten vom laufenden Jahr die älter als 90 Tage sind → ins laufende Jahresarchiv
        remaining = db.conn.execute(
            "SELECT COUNT(*) AS cnt FROM measurements WHERE dateutc < ?",
            (f"{cutoff} 00:00:00",)
        ).fetchone()
        remaining_count = remaining["cnt"] if remaining else 0

        if remaining_count > 0:
            log.info("Archiviere %d verbleibende Zeilen (laufendes Jahr %s)", remaining_count, current_year)
            archive_conn = _ensure_archive_db(current_year)
            try:
                batch_size = 10_000
                while True:
                    rows = db.conn.execute(
                        "SELECT * FROM measurements WHERE dateutc < ? ORDER BY dateutc LIMIT ?",
                        (f"{cutoff} 00:00:00", batch_size)
                    ).fetchall()

                    if not rows:
                        break

                    cols = rows[0].keys()
                    placeholders = ",".join(["?"] * len(cols))
                    archive_conn.executemany(
                        f"INSERT OR IGNORE INTO measurements ({','.join(cols)}) VALUES ({placeholders})",
                        [tuple(r) for r in rows]
                    )
                    archive_conn.commit()

                    last_ts = rows[-1]["dateutc"]
                    first_ts = rows[0]["dateutc"]
                    db.conn.execute(
                        "DELETE FROM measurements WHERE dateutc >= ? AND dateutc <= ?",
                        (first_ts, last_ts)
                    )
                    db.conn.commit()

                    stats["archived"] += len(rows)
                    stats["deleted"] += len(rows)

                    if len(rows) < batch_size:
                        break

                if current_year not in stats["years"]:
                    stats["years"].append(current_year)
            finally:
                archive_conn.close()

    # 4. VACUUM wenn viel gelöscht wurde
    if stats["deleted"] > 50_000:
        log.info("VACUUM der Haupt-DB...")
        db.conn.execute("VACUUM")

    log.info(
        "Cleanup abgeschlossen: %d Zeilen archiviert, Jahre: %s",
        stats["archived"], ", ".join(stats["years"]) or "keine"
    )
    return stats


# ─── Async Scheduler ─────────────────────────────────────────

async def _schedule_loop(db):
    """Wartet bis 02:00 Uhr und führt dann den Cleanup durch. Wiederholt täglich."""
    while True:
        now = datetime.now(timezone.utc)
        # Nächstes 02:00 UTC berechnen
        target = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        log.info("Nächster Cleanup in %.1f Stunden (um %s UTC)", wait_seconds / 3600, target.strftime("%H:%M"))
        await asyncio.sleep(wait_seconds)

        try:
            run_cleanup(db)
        except Exception as e:
            log.error("Cleanup fehlgeschlagen: %s", e, exc_info=True)


def start_cleanup_scheduler(db) -> asyncio.Task:
    """Startet den nächtlichen Cleanup als asyncio-Task."""
    return asyncio.create_task(_schedule_loop(db))
