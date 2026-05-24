#!/bin/bash
# ==============================================================
# Kopiert die DB von hc_espe (v1) nach hc_p1me (v2)
# ==============================================================
# Verwendet SQLite .backup für konsistente Kopie während v1 läuft.
#
# Verwendung:
#   cd apps_v2/hc_p1me
#   bash scripts/copy_db_from_v1.sh
# ==============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

SOURCE_DB="${PROJECT_DIR}/../../apps_v1/hc_espe/data/energy.db"
TARGET_DB="${PROJECT_DIR}/data/energy.db"
BACKUP_DB="${PROJECT_DIR}/data/energy.db.backup"

echo "============================================================"
echo "DB-Kopie: hc_espe (v1) -> hc_p1me (v2)"
echo "============================================================"
echo "  Quelle: ${SOURCE_DB}"
echo "  Ziel:   ${TARGET_DB}"
echo ""

# Prüfe ob Quell-DB existiert
if [ ! -f "$SOURCE_DB" ]; then
    echo "❌ Quell-DB nicht gefunden: $SOURCE_DB"
    exit 1
fi

# Prüfe ob v2 läuft (DB gelockt)
if lsof "$TARGET_DB" 2>/dev/null | grep -q "energy.db"; then
    echo "⚠️  WARNUNG: hc_p1me (v2) läuft noch!"
    echo "   Bitte stoppen: Ctrl+C im Terminal wo 'make dev' läuft"
    exit 1
fi

# Backup der alten v2-DB
if [ -f "$TARGET_DB" ]; then
    echo "  Sichere alte v2-DB..."
    mv "$TARGET_DB" "$BACKUP_DB"
    echo "  ✓ Backup: ${BACKUP_DB}"
fi

# Konsistente Kopie mit SQLite .backup
echo "  Kopiere DB von v1 (konsistent, auch wenn v1 läuft)..."
sqlite3 "$SOURCE_DB" ".backup '$TARGET_DB'"

# Größe prüfen
SOURCE_SIZE=$(du -h "$SOURCE_DB" | cut -f1)
TARGET_SIZE=$(du -h "$TARGET_DB" | cut -f1)

echo ""
echo "============================================================"
echo "  ✅ DB kopiert"
echo "  Quelle: ${SOURCE_SIZE}"
echo "  Ziel:   ${TARGET_SIZE}"
echo "============================================================"
echo ""
echo "Jetzt v2 starten: make dev"
