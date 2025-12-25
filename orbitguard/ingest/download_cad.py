"""
Downloads close-approach data from NASA/JPL SBDB CAD API and saves the following: 
- data/raw/cad.json
- data/raw/cad.csv - (CSV version for db readings)

CAD records contain fields like:
des, orbit_id, jd, cd, dist, dist_min, dist_max, v_rel, v_inf, ...
(dist is in AU, v_rel is in km/s)  (see CAD API docs)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

BASE_URL = "https://ssd-api.jpl.nasa.gov/cad.api"

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

JSON_PATH = RAW_DIR / "cad.json"
CSV_PATH = RAW_DIR / "cad.csv"


def download_cad_json(
    dist_max: str = "0.05", # AU by default
    date_min: str = "now",
    date_max: str = "+60",     
    body: str = "Earth",
    sort: str = "date",
) -> dict:
    params = {
        "dist-max": dist_max,
        "date-min": date_min,
        "date-max": date_max,
        "body": body,
        "sort": sort,
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    print("Request URL:", url)


    req = Request(url, headers={"User-Agent": "OrbitGuard/0.1 (edu project)"})
    with urlopen(req) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload


def write_csv_from_payload(payload: dict, csv_path: Path) -> None:
    # CAD API returns:
    #list of field names
    #list of rows (each row is a list)
    fields = payload.get("fields")
    data = payload.get("data")

    if not fields or not data:
        # If count == 0, "data" may be missing
        raise ValueError("No CAD data returned (payload has no fields/data).")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        writer.writerows(data)


def main() -> None:
    payload = download_cad_json()

    #save raw JSON
    JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    #save CSV
    write_csv_from_payload(payload, CSV_PATH)

    print(f"Saved: {JSON_PATH}")
    print(f"Saved: {CSV_PATH}")
    print(f"Records: {payload.get('count')}")


if __name__ == "__main__":
    main()