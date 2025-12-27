"""
Ingests NASA/JPL CAD close-approach data from a cad.csv into SQLite

What the CAD data means:
- Each row is a single close-approach event for one object relative to Earth
- It includes:
  - object identifier (des / fullname)
  - close-approach time ("cd")
  - miss distance ("dist", in AU)
  - relative velocity ("v_rel", in km/s)

What this script does:
- Reads data/raw/cad.csv (produced by download_cad.py)
- Parses the CAD "cd" time into unix time
- Converts miss distance from AU to km
- Inserts each row as an ApproachEvent in the database

Why we store ApproachEvent (not full orbits):
- OrbitGuard's MVP is an evaluation engine, not an orbit propagator
- We treat CAD's published close-approach events as the “ground truth” inputs
  for scanning time windows and flagging risks deterministically
"""

from __future__ import annotations

import csv
from pathlib import Path

from orbitguard.db.database import SessionLocal
from orbitguard.db.models import ApproachEvent
from orbitguard.ingest.parse_time import parse_cd_to_unix_seconds

AU_TO_KM = 149_597_870.7

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = REPO_ROOT / "data" / "raw" / "cad.csv"


def main() -> None:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"Missing {RAW_CSV}. Run download_cad first.")

    inserted = 0
    skipped = 0

    db = SessionLocal()
    try:
        with RAW_CSV.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                des = (row.get("des") or "").strip()
                cd = (row.get("cd") or "").strip()
                dist_au = row.get("dist")
                v_rel = row.get("v_rel")

                if not des or not cd or dist_au is None or v_rel is None:
                    skipped += 1
                    continue

                approach_ts = parse_cd_to_unix_seconds(cd)
                miss_distance_km = float(dist_au) * AU_TO_KM
                v_rel_km_s = float(v_rel)

                event = ApproachEvent(
                    object_id=des,
                    name=row.get("fullname") or des,
                    approach_ts=approach_ts,
                    miss_distance_km=miss_distance_km,
                    v_rel_km_s=v_rel_km_s,
                    source="NASA_JPL_CAD",
                )
                db.add(event)
                inserted += 1

        db.commit()
        print(f"✅ Ingested CAD events. Inserted={inserted}, Skipped={skipped}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
