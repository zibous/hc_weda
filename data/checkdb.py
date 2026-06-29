#!/usr/bin/env python3
import sqlite3
import argparse
import logging
from pathlib import Path
import shutil
import csv

DB_PATH = Path("weather.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("db-check")


# ------------------------------------------------------------
# Hilfsfunktion: Jahr-Filter korrekt erzeugen
# ------------------------------------------------------------
def build_year_filter(jahr):
    if jahr is None:
        return ""
    return f" AND dateutc LIKE '{jahr}-%'"


# ------------------------------------------------------------
# ECHTE Fehler (werden gelöscht)
# ------------------------------------------------------------
DELETE_QUERIES = {
    "Temperatur unplausibel (tempf < -40 oder > 150)": """
        SELECT * FROM measurements
        WHERE (tempf < -40 OR tempf > 150)
        {YEAR_FILTER};
    """,

    "Fehlerwerte -9999 (alle Felder)": """
        SELECT * FROM measurements
        WHERE (tempf = -9999
           OR dewptf = -9999
           OR windchillf = -9999
           OR humidity = -9999
           OR windspeedmph = -9999
           OR winddir = -9999
           OR baromin = -9999
           OR solarradiation = -9999
           OR uv = -9999)
        {YEAR_FILTER};
    """,

    "Solar unplausibel (> 2000 oder < 0)": """
        SELECT * FROM measurements
        WHERE (solarradiation > 2000 OR solarradiation < 0)
        {YEAR_FILTER};
    """,

    "UV unplausibel (> 15 oder < 0)": """
        SELECT * FROM measurements
        WHERE (uv > 15 OR uv < 0)
        {YEAR_FILTER};
    """,

    "Windgeschwindigkeit unplausibel (<0 oder >150 mph)": """
        SELECT * FROM measurements
        WHERE (windspeedmph < 0 OR windspeedmph > 150)
        {YEAR_FILTER};
    """,

    "Windrichtung unplausibel (<0 oder >360)": """
        SELECT * FROM measurements
        WHERE (winddir < 0 OR winddir > 360)
        {YEAR_FILTER};
    """,

    "Luftdruck unplausibel (<25 oder >32 inHg)": """
        SELECT * FROM measurements
        WHERE (baromin < 25 OR baromin > 32)
        {YEAR_FILTER};
    """
}


# ------------------------------------------------------------
# Diagnose (niemals löschen)
# ------------------------------------------------------------
DIAGNOSE_QUERIES = {
    "Wind stuck (immer gleiche Geschwindigkeit)": """
        SELECT dateutc FROM measurements
        WHERE windspeedmph IN (
            SELECT windspeedmph
            FROM measurements
            GROUP BY windspeedmph
            HAVING COUNT(*) > 100
        )
        {YEAR_FILTER};
    """,

    "Regen stuck (immer gleiche Werte)": """
        SELECT dateutc FROM measurements
        WHERE rainin IN (
            SELECT rainin
            FROM measurements
            GROUP BY rainin
            HAVING COUNT(*) > 100
        )
        {YEAR_FILTER};
    """
}


# ------------------------------------------------------------
def backup_db():
    backup = DB_PATH.with_suffix(".backup.db")
    shutil.copy(DB_PATH, backup)
    log.warning("🔒 Backup erstellt: %s", backup)


# ------------------------------------------------------------
def export_csv(rows, filename="db_errors.csv"):
    if not rows:
        return

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([col for col in rows[0].keys()])
        for row in rows:
            writer.writerow([row[col] for col in row.keys()])

    log.warning("📄 Fehlerhafte Datensätze exportiert nach %s", filename)


# ------------------------------------------------------------
def run_diagnose(conn, jahr):
    year_filter = build_year_filter(jahr)

    log.info("🟦 Diagnose (wird NICHT gelöscht):")
    for desc, sql in DIAGNOSE_QUERIES.items():
        sql = sql.replace("{YEAR_FILTER}", year_filter)
        cur = conn.execute(sql)
        rows = cur.fetchall()
        log.info("  %s: %d", desc, len(rows))


# ------------------------------------------------------------
def collect_errors(conn, jahr):
    cur = conn.cursor()
    bad_rows = []

    year_filter = build_year_filter(jahr)

    log.warning("🟥 Löschbare Fehler:")
    for description, sql in DELETE_QUERIES.items():
        sql = sql.replace("{YEAR_FILTER}", year_filter)
        cur.execute(sql)
        rows = cur.fetchall()

        if rows:
            log.warning("  %s: %d", description, len(rows))
            bad_rows.extend(rows)
        else:
            log.info("  %s: OK", description)

    log.warning("➡️  Summe löschbare Datensätze: %d", len(bad_rows))
    return bad_rows


# ------------------------------------------------------------
def delete_errors(conn, rows):
    if not rows:
        log.info("Keine fehlerhaften Datensätze zum Löschen.")
        return

    cur = conn.cursor()
    log.warning("🗑️  Lösche %d Datensätze…", len(rows))

    cur.executemany(
        "DELETE FROM measurements WHERE dateutc = ?;",
        [(r["dateutc"],) for r in rows]
    )
    conn.commit()

    log.warning("✔️  Löschen abgeschlossen.")


# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jahr", type=int, help="Nur Datensätze eines bestimmten Jahres prüfen")
    parser.add_argument("-fixerrors", action="store_true")
    parser.add_argument("-export", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        log.error("Datenbank nicht gefunden: %s", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    log.info("Starte Datenbankprüfung…")

    run_diagnose(conn, args.jahr)

    bad_rows = collect_errors(conn, args.jahr)

    if args.export:
        export_csv(bad_rows)

    if args.fixerrors:
        backup_db()
        delete_errors(conn, bad_rows)
    else:
        log.info("Nur Anzeige-Modus (verwende -fixerrors zum Löschen).")

    conn.close()
    log.info("Fertig.")


if __name__ == "__main__":
    main()
