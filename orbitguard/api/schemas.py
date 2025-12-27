#What this file does: 
'''
 - validates input automatically: ScanCreate tells fastapi 
 --- what fields must exist (start_ts, end_ts, threshold_km)
 --- what types they should be in (int, float)
 --- additional rules (threshold km > 0, etc.)
 - defines what the api returns
 --- scanout defines the shape of the response and it will always return in same structure
'''

from pydantic import BaseModel, Field
from orbitguard.api.time_utils import to_unix_seconds
from pydantic import BaseModel, field_validator
from datetime import datetime

class ScanCreate(BaseModel):
    # Users can send int unix seconds OR ISO strings OR datetimes
    start_ts: int | str | datetime
    end_ts: int | str | datetime
    threshold_km: float

    @field_validator("start_ts", "end_ts", mode="before")
    @classmethod
    def _parse_ts(cls, v):
        return to_unix_seconds(v)


class ScanOut(BaseModel):
    id: int
    start_ts: int
    end_ts: int
    threshold_km: float
    status: str
    attempts: int
    max_attempts: int
    error: str | None

class RiskOut(BaseModel):
    id: int
    job_id: int
    object_id: str
    min_distance_km: float
    tca_ts: int
    risk_score: float

class ScanSummaryOut(BaseModel):
    job_id: int
    status: str
    window_start_ts: int
    window_end_ts: int
    threshold_km: float
    events_in_window: int
    risks_found: int

