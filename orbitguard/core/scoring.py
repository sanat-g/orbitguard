'''
- Risk Score: 
-- computes a risk score in the range of 0 to 1 to quantify the closeness of an object
-- score = 1 - (min_distance/threshold)
-- a closer object scores higher

- Build Explanation JSON: 
-- builds a JSON string that stores the inputs and outputs of a scan result. Is stored in SQLite
'''


from __future__ import annotations
import json


def risk_score(threshold_km: float, min_distance_km: float) -> float:
    if threshold_km <= 0:
        return 0.0
    s = 1.0 - (min_distance_km / threshold_km)
    return max(0.0, min(1.0, s))

def build_explanation_json(
    object_id: str,
    epoch_ts: int,
    start_ts: int,
    end_ts: int,
    threshold_km: float,
    tca_ts: int,
    min_distance_km: float,
    score: float,
) -> str:
    """
    stored as JSON text (easy for SQLite).
    """
    payload = {
        "object_id": object_id,
        "window": {"start_ts": start_ts, "end_ts": end_ts},
        "epoch_ts": epoch_ts,
        "closest_approach": {"tca_ts": tca_ts, "min_distance_km": min_distance_km},
        "threshold_km": threshold_km,
        "risk_score": score,
        "why_flagged": min_distance_km <= threshold_km,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
