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
            # Treat as UTC for MVP.
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError as e:
            last_err = e
    raise ValueError(f"Unrecognized date format for cd='{cd}': {last_err}")
