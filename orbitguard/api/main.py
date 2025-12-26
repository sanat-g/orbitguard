from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from orbitguard.db.models import RiskEvent, Alert, AlertStatus
from orbitguard.api.schemas import RiskOut, AlertOut
from orbitguard.api.deps import get_db
from orbitguard.api.schemas import ScanCreate, ScanOut
from orbitguard.db.models import ScanJob, JobStatus
from orbitguard.api.schemas import ScanSummaryOut
from orbitguard.db.models import ScanJob, ApproachEvent, RiskEvent, Alert
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="OrbitGuard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

@app.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertOut(
        id=alert.id,
        object_id=alert.object_id,
        tca_ts=alert.tca_ts,
        min_distance_km=alert.min_distance_km,
        risk_score=alert.risk_score,
        status=alert.status,
        dedupe_key=alert.dedupe_key,
    )


@app.post("/alerts/{alert_id}/ack", response_model=AlertOut)
def ack_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Idempotent: acking an already ACKED/RESOLVED alert shouldn't error
    if alert.status == AlertStatus.OPEN.value:
        alert.status = AlertStatus.ACKED.value
        db.commit()
        db.refresh(alert)

    return AlertOut(
        id=alert.id,
        object_id=alert.object_id,
        tca_ts=alert.tca_ts,
        min_distance_km=alert.min_distance_km,
        risk_score=alert.risk_score,
        status=alert.status,
        dedupe_key=alert.dedupe_key,
    )


@app.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Idempotent: resolving an already RESOLVED alert shouldn't error
    if alert.status != AlertStatus.RESOLVED.value:
        alert.status = AlertStatus.RESOLVED.value
        db.commit()
        db.refresh(alert)

    return AlertOut(
        id=alert.id,
        object_id=alert.object_id,
        tca_ts=alert.tca_ts,
        min_distance_km=alert.min_distance_km,
        risk_score=alert.risk_score,
        status=alert.status,
        dedupe_key=alert.dedupe_key,
    )

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


@app.get("/scans/{job_id}/summary", response_model=ScanSummaryOut)
def scan_summary(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # How many CAD events exist inside the requested window?
    events_in_window = (
        db.query(ApproachEvent)
        .filter(ApproachEvent.approach_ts >= job.start_ts)
        .filter(ApproachEvent.approach_ts <= job.end_ts)
        .count()
    )

    # How many risks did THIS job produce?
    risks_found = (
        db.query(RiskEvent)
        .filter(RiskEvent.job_id == job.id)
        .count()
    )

    # How many alerts correspond to risks from THIS job?
    # (simple linkage by object_id + tca_ts match)
    alerts_linked = (
        db.query(Alert)
        .join(
            RiskEvent,
            (Alert.object_id == RiskEvent.object_id) & (Alert.tca_ts == RiskEvent.tca_ts),
        )
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
        alerts_linked=alerts_linked,
    )
