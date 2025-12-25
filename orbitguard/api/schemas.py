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

class ScanCreate(BaseModel):
    start_ts: int = Field(..., description="Unix timestamp (seconds)")
    end_ts: int = Field(..., description="Unix timestamp (seconds)")
    threshold_km: float = Field(..., gt=0, description="Distance threshold in km")

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

class AlertOut(BaseModel):
    id: int
    object_id: str
    tca_ts: int
    min_distance_km: float
    risk_score: float
    status: str
    dedupe_key: str
