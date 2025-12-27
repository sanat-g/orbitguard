'''
Helper file for ingestion. 

The NASA/JPL CAD data contains close-approach date/time data (stored in a field called "cd")
The time and date is given in string formats like "2025-Nov-23 18:00", "2025-Nov-21 12:03:03", etc. 

What this file does: 
-- converts a CAD "cd" string into an integer Unix timestamp (seconds since Jan 1, 1970 UTC)

Why this is needed: 
-- OrbitGuard stores time in unix seconds so comparisions in the database stay simple and consistent. 


'''

from __future__ import annotations

from datetime import datetime, timezone

# CAD "cd" format must be converted to compute for our model
#time will be converted to unix seconds
FORMATS = [
    "%Y-%b-%d %H:%M",
    "%Y-%b-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]

def parse_cd_to_unix_seconds(cd: str) -> int:
    cd = cd.strip()
    last_err = None
    for fmt in FORMATS:
        try:
            dt = datetime.strptime(cd, fmt)
            # treated as utc for mvp
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError as e:
            last_err = e
    raise ValueError(f"Unrecognized date format for cd='{cd}': {last_err}")
