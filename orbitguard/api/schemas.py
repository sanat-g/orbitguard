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
