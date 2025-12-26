from __future__ import annotations

from datetime import datetime, timezone

def to_unix_seconds(value) -> int:
    """
    Accepts:
      - int (already unix seconds)
      - str (ISO like '2026-01-15T12:00:00Z' or unix as '1766638719')
      - datetime
    Returns:
      - unix timestamp (int seconds, UTC)
    """
    if isinstance(value, int):
        return value

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return int(dt.timestamp())

    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return int(s)

        s = s.replace("Z", "+00:00")

        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return int(dt.timestamp())

    raise ValueError(f"Unsupported time value: {value!r}")
