"""
FastAPI application for OrbitGuard.

What this file does:
- Creates the HTTP API server that the UI and tools talk to
- Enables CORS so a browser-based UI (served from localhost) can call the API
- Exposes endpoints to:
  - health-check the server
  - create scan jobs (queued work)
  - fetch scan job status
  - list risk results produced by the worker
  - fetch stored explanations for a risk
  - return a summary for a scan job (counts of events scanned + risks found)
"""


from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from orbitguard.api.deps import get_db
from orbitguard.api.schemas import ScanCreate, ScanOut, RiskOut, ScanSummaryOut
from orbitguard.db.models import ScanJob, JobStatus, ApproachEvent, RiskEvent


app = FastAPI(title="OrbitGuard")

# Allow the browser UI (ui/index.html served on a simple local server) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoint to check whether the server is alive
@app.get("/health")
def health():
    return {"status": "ok"}


# Create a scan job (does NOT run it immediately)
@app.post("/scans", response_model=ScanOut)
def create_scan(scan: ScanCreate, db: Session = Depends(get_db)):
    # basic validation (business rules)
    if scan.end_ts <= scan.start_ts:
        raise HTTPException(status_code=400, detail="end_ts must be greater than start_ts")

    job = ScanJob(
        start_ts=scan.start_ts,
        end_ts=scan.end_ts,
        threshold_km=scan.threshold_km,
        status=JobStatus.PENDING.value,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return ScanOut(
        id=job.id,
        start_ts=job.start_ts,
        end_ts=job.end_ts,
        threshold_km=job.threshold_km,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        error=job.error,
    )


# Get scan job status/details
@app.get("/scans/{job_id}", response_model=ScanOut)
def get_scan(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Scan job not found")

    return ScanOut(
        id=job.id,
        start_ts=job.start_ts,
        end_ts=job.end_ts,
        threshold_km=job.threshold_km,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        error=job.error,
    )


# List risks (optionally filtered to a specific job)
@app.get("/risks", response_model=list[RiskOut])
def list_risks(job_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(RiskEvent)
    if job_id is not None:
        q = q.filter(RiskEvent.job_id == job_id)

    risks = q.order_by(RiskEvent.risk_score.desc()).all()

    return [
        RiskOut(
            id=r.id,
            job_id=r.job_id,
            object_id=r.object_id,
            min_distance_km=r.min_distance_km,
            tca_ts=r.tca_ts,
            risk_score=r.risk_score,
        )
        for r in risks
    ]


# Explain a specific risk (returns stored explanation)
@app.get("/risks/{risk_id}/explain")
def explain_risk(risk_id: int, db: Session = Depends(get_db)):
    risk = db.query(RiskEvent).filter(RiskEvent.id == risk_id).first()
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")

    return {
        "risk_id": risk.id,
        "object_id": risk.object_id,
        "min_distance_km": risk.min_distance_km,
        "tca_ts": risk.tca_ts,
        "risk_score": risk.risk_score,
        "explanation_json": risk.explanation_json,
    }


# Scan summary (no alerts)
@app.get("/scans/{job_id}/summary", response_model=ScanSummaryOut)
def scan_summary(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Scan job not found")

    events_in_window = (
        db.query(ApproachEvent)
        .filter(ApproachEvent.approach_ts >= job.start_ts)
        .filter(ApproachEvent.approach_ts <= job.end_ts)
        .count()
    )

    risks_found = (
        db.query(RiskEvent)
        .filter(RiskEvent.job_id == job.id)
        .count()
    )

    return ScanSummaryOut(
        job_id=job.id,
        status=job.status,
        window_start_ts=job.start_ts,
        window_end_ts=job.end_ts,
        threshold_km=job.threshold_km,
        events_in_window=events_in_window,
        risks_found=risks_found,
    )