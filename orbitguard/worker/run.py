'''
Background worker for scan jobs. 

What it does: 
-- Checks the database for the oldest pending scan job
-- Claims the job by changing its status to "running" (so two workers don't do the same job)
-- Scans all the stored ApproachEvent rows that fall within the job's time window 
-- Flags events whose miss distance is less than or equal to threshold km and writes RiskEvent rows
-- Stores an explanation JSON for each risk (shows why it was flagged)
-- Marks the job as succeeded once finished, or failed if error occurs

'''


from __future__ import annotations
from sqlalchemy.orm import Session

from orbitguard.db.database import SessionLocal
from orbitguard.db.models import ApproachEvent, ScanJob, RiskEvent, JobStatus
from orbitguard.core.scoring import risk_score, build_explanation_json


def claim_next_job(db: Session) -> ScanJob | None:
    """
    Find the oldest pending job and mark it as RUNNING so it won't be picked up again.
    """
    job = (
        db.query(ScanJob)
        .filter(ScanJob.status == JobStatus.PENDING.value)
        .order_by(ScanJob.created_at.asc())
        .first()
    )
    if job is None:
        return None

    job.status = JobStatus.RUNNING.value
    job.error = None
    db.commit()
    db.refresh(job)
    return job


def process_job(db: Session, job: ScanJob) -> None:
    """
    CAD-correct scan:
    - Each ApproachEvent already represents a closest-approach event at approach_ts
    - We flag an event if:
        job.start_ts <= approach_ts <= job.end_ts
        AND miss_distance_km <= job.threshold_km

    For each flagged event we create a RiskEvent (per-job result record).
    """
    events = (
        db.query(ApproachEvent)
        .filter(ApproachEvent.approach_ts >= job.start_ts)
        .filter(ApproachEvent.approach_ts <= job.end_ts)
        .all()
    )

    for ev in events:
        dmin = ev.miss_distance_km
        tca_ts = ev.approach_ts

        if dmin <= job.threshold_km:
            score = risk_score(job.threshold_km, dmin)

            expl = build_explanation_json(
                object_id=ev.object_id,
                epoch_ts=ev.approach_ts,   # for CAD, epoch == approach time
                start_ts=job.start_ts,
                end_ts=job.end_ts,
                threshold_km=job.threshold_km,
                tca_ts=tca_ts,
                min_distance_km=dmin,
                score=score,
            )

            risk = RiskEvent(
                job_id=job.id,
                object_id=ev.object_id,
                min_distance_km=dmin,
                tca_ts=tca_ts,
                risk_score=score,
                explanation_json=expl,
            )
            db.add(risk)

    # Commit once at the end (faster + cleaner than committing per row)
    db.commit()


def run_once() -> None:
    """
    Runs a single job and then exits.
    """
    db = SessionLocal()
    try:
        job = claim_next_job(db)
        if job is None:
            print("No pending jobs.")
            return

        print(f"Running job {job.id} window=({job.start_ts}, {job.end_ts}) threshold={job.threshold_km} km")
        try:
            process_job(db, job)
            job.status = JobStatus.SUCCEEDED.value
            db.commit()
            print(f"Job {job.id} succeeded.")
        except Exception as e:
            db.rollback()
            job.attempts += 1
            job.error = str(e)

            if job.attempts < job.max_attempts:
                job.status = JobStatus.PENDING.value
                print(
                    f"Job {job.id} failed; retrying later "
                    f"(attempt {job.attempts}/{job.max_attempts}). Error: {e}"
                )
            else:
                job.status = JobStatus.FAILED.value
                print(f"Job {job.id} failed permanently. Error: {e}")

            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_once()
