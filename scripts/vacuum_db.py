#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VACUUM Database
===============
Komprimiert die SQLite-Datenbank und gibt Speicherplatz frei.

Verwendung:
  python scripts/vacuum_db.py
"""

import sys
from pathlib import Path

# Projektroot zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import DB_PATH
from app.services.database import EnergyDB


def main():
    print("=" * 60)
    print("VACUUM Database")
    print("=" * 60)

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"❌ Datenbank nicht gefunden: {db_path}")
        return 1

    # Größe vor VACUUM
    size_before = db_path.stat().st_size / (1024 * 1024)
    print(f"  Größe vorher: {size_before:.1f} MB")

    # VACUUM durchführen
    print("  Führe VACUUM durch...")
    db = EnergyDB(str(db_path))
    db.conn.execute("VACUUM")
    db.conn.commit()

    # Statistiken
    stats = db.get_stats()
    print(f"  Readings:     {stats['readings']:,}")
    print(f"  Days:         {stats['days']:,}")

    db.close()

    # Größe nach VACUUM
    size_after = db_path.stat().st_size / (1024 * 1024)
    saved = size_before - size_after
    print(f"  Größe nachher: {size_after:.1f} MB")
    print(f"  Gespart:       {saved:.1f} MB ({saved/size_before*100:.1f}%)")
    print("=" * 60)
    print("✅ VACUUM abgeschlossen")

    return 0

if __name__ == "__main__":
    sys.exit(main())
