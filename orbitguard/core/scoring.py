from __future__ import annotations
import json

def risk_score(threshold_km: float, min_distance_km: float) -> float:
    """
    Simple score in [0, 1].
    Higher score = closer to earth

    If min_distance == threshold -> 0.5
    If min_distance much smaller -> approaches 1+
    If min_distance bigger -> below 0.5

    """
    if min_distance_km <= 0:
        return 1.0
    ratio = threshold_km / min_distance_km
    # Clamp for mvp purposes
    return max(0.0, min(1.0, ratio))

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
