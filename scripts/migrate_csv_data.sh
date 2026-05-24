#!/bin/bash
# ==============================================================
# Migration: hc_espe CSV-Daten -> hc_p1me/data/tasmota/
# ==============================================================
# Kopiert die bestehenden CSV-Dateien aus hc_espe nach
# hc_p1me/data/tasmota/ (gleiche Ordnerstruktur).
#
# Verwendung:
#   cd apps_v2/hc_p1me
#   bash scripts/migrate_csv_data.sh
#
# Hinweis: Kopiert nur, löscht nichts im Quellverzeichnis.
# ==============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Quellverzeichnis (hc_espe)
SOURCE_DIR="${PROJECT_DIR}/../../apps_v1/hc_espe/data"

# Zielverzeichnis
TARGET_DIR="${PROJECT_DIR}/data/tasmota"

echo "============================================================"
echo "Migration: hc_espe CSV -> hc_p1me/data/tasmota/"
echo "============================================================"
echo "  Quelle:  ${SOURCE_DIR}"
echo "  Ziel:    ${TARGET_DIR}"
echo ""

# Prüfe ob Quellverzeichnis existiert
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Quellverzeichnis nicht gefunden: $SOURCE_DIR"
    exit 1
fi

# Zielverzeichnis erstellen
mkdir -p "$TARGET_DIR"

# Zähler
copied=0
skipped=0

# Alle YYYY-Ordner mit CSV-Dateien kopieren
for year_dir in "$SOURCE_DIR"/[0-9][0-9][0-9][0-9]; do
    if [ ! -d "$year_dir" ]; then
        continue
    fi

    year=$(basename "$year_dir")
    target_year_dir="$TARGET_DIR/$year"
    mkdir -p "$target_year_dir"

    for csv_file in "$year_dir"/*.csv; do
        if [ ! -f "$csv_file" ]; then
            continue
        fi

        filename=$(basename "$csv_file")
        target_file="$target_year_dir/$filename"

        if [ -f "$target_file" ]; then
            echo "  ⏭️  Übersprungen (existiert): $year/$filename"
            skipped=$((skipped + 1))
        else
            cp "$csv_file" "$target_file"
            echo "  ✓ Kopiert: $year/$filename"
            copied=$((copied + 1))
        fi
    done
done

echo ""
echo "============================================================"
echo "  Kopiert:     $copied Dateien"
echo "  Übersprungen: $skipped Dateien"
echo "  Ziel:        $TARGET_DIR"
echo "============================================================"

# Übersicht
echo ""
echo "Ordnerstruktur:"
find "$TARGET_DIR" -name "*.csv" | sort | head -20
total=$(find "$TARGET_DIR" -name "*.csv" | wc -l)
echo "  ... ($total CSV-Dateien gesamt)"
