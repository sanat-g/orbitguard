from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from orbitguard.db.models import RiskEvent, Alert
from orbitguard.api.schemas import RiskOut, AlertOut
from orbitguard.api.deps import get_db
from orbitguard.api.schemas import ScanCreate, ScanOut
from orbitguard.db.models import ScanJob, JobStatus

app = FastAPI(title="OrbitGuard")

#Endpoint to check whether the server is alive
@app.get("/health")
def health():
    return {"status": "ok"}

#The endpoint creates a scan job and stores it in the database. 
#response_model = ScanOut: means FastAPI will validate your return object matches ScanOut shape
@app.post("/scans", response_model=ScanOut)
def create_scan(scan: ScanCreate, db: Session = Depends(get_db)):
    # basic validation (business rules)
    if scan.start_ts >= scan.end_ts:
        raise HTTPException(status_code=400, detail="start_ts must be < end_ts")

    #Creates a ScanJob ORM object (not yet written to db)
    job = ScanJob(
        start_ts=scan.start_ts,
        end_ts=scan.end_ts,
        threshold_km=scan.threshold_km,
        status=JobStatus.PENDING.value,
    )

    db.add(job)
    #Write changes to db
    db.commit()
    db.refresh(job)  # pulls generated id + defaults from DB

    #return a response object matching ScanOut (converting orm -> pydantic model)
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


#Endpoint lets you check the status and details of a scan job based on its id. 
@app.get("/scans/{job_id}", response_model=ScanOut)
def get_scan(job_id: int, db: Session = Depends(get_db)):
    #look for the row in table with that id
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    #if no row exists, return error
    if job is None:
        raise HTTPException(status_code=404, detail="Scan job not found")

    #return the job's fields as json, in scanout format
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


@app.get("/alerts", response_model=list[AlertOut])
def list_alerts(status: str | None = "OPEN", db: Session = Depends(get_db)):
    q = db.query(Alert)
    if status is not None:
        q = q.filter(Alert.status == status)

    alerts = q.order_by(Alert.risk_score.desc()).all()

    return [
        AlertOut(
            id=a.id,
            object_id=a.object_id,
            tca_ts=a.tca_ts,
            min_distance_km=a.min_distance_km,
            risk_score=a.risk_score,
            status=a.status,
            dedupe_key=a.dedupe_key,
        )
        for a in alerts
    ]


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
