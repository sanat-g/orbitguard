from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

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