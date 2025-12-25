"""
What this worker does:
- Looks for the next pending scan job in the database
- Marks it as running so it won't be picked up again
- Loads all objects from the objects table
- For each object, program computes its closest approach to Earth within the job's time window
- If the object comes within the threshold distance, it:
    - writes a RiskEvent (per-job result record)
    - creates/updates an Alert (deduped so you don't spam duplicates)
- Marks the job succeeded if everything goes well
- On error, increments attempts and either retries later or marks failed
"""

from __future__ import annotations

import time
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from orbitguard.db.database import SessionLocal
from orbitguard.db.models import Object, ScanJob, RiskEvent, Alert, JobStatus, AlertStatus
from orbitguard.core.scan_math import closest_approach_constant_velocity
from orbitguard.core.scoring import risk_score, build_explanation_json


def hour_bucket(ts: int) -> int:
    """rounds timestamp down to the start of its hour, so alerts don't spam duplicates"""
    return ts - (ts % 3600)


def claim_next_job(db: Session) -> ScanJob | None:
    """
    Find the oldest pending job and atomically mark it as running.
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


def create_alert_deduped(
    db: Session,
    object_id: str,
    tca_ts: int,
    min_distance_km: float,
    score: float,
    threshold_km: float,
) -> None:
    """
    creates an open alert for a risky object, while preventing duplicates. 

        - We build a dedupe_key from:
        (object_id, hour_bucket(tca_ts), threshold_km)

        if an alert with this key already exists, we know it's a duplicate. 

    """
    dedupe_key = f"{object_id}:{hour_bucket(tca_ts)}:{int(threshold_km)}"

    alert = Alert(
        object_id=object_id,
        tca_ts=tca_ts,
        min_distance_km=min_distance_km,
        risk_score=score,
        status=AlertStatus.OPEN.value,
        dedupe_key=dedupe_key,
    )
    db.add(alert)
    try:
        db.commit()
    except IntegrityError:
        # Dedupe hit: alert already exists, so do nothing
        db.rollback()


def process_job(db: Session, job: ScanJob) -> None:
    """
    Runs the actual scan math for one job

    For every object in the database:
      - Compute (tca_ts, min_distance_km) within [job.start_ts, job.end_ts]
      - If min_distance_km <= job.threshold_km:
          - compute a risk score
          - build an explanation JSON structure
          - write a RiskEvent row
          - create a deduped Alert
    """
    objects = db.query(Object).all()

    for obj in objects:
        tca_ts, dmin = closest_approach_constant_velocity(
            epoch_ts=obj.epoch_ts,
            x_km=obj.x_km, y_km=obj.y_km, z_km=obj.z_km,
            vx_km_s=obj.vx_km_s, vy_km_s=obj.vy_km_s, vz_km_s=obj.vz_km_s,
            start_ts=job.start_ts,
            end_ts=job.end_ts,
        )

        if dmin <= job.threshold_km:
            score = risk_score(job.threshold_km, dmin)
            expl = build_explanation_json(
                object_id=obj.object_id,
                epoch_ts=obj.epoch_ts,
                start_ts=job.start_ts,
                end_ts=job.end_ts,
                threshold_km=job.threshold_km,
                tca_ts=tca_ts,
                min_distance_km=dmin,
                score=score,
            )

            risk = RiskEvent(
                job_id=job.id,
                object_id=obj.object_id,
                min_distance_km=dmin,
                tca_ts=tca_ts,
                risk_score=score,
                explanation_json=expl,
            )
            db.add(risk)
            db.commit() 

            create_alert_deduped(
                db=db,
                object_id=obj.object_id,
                tca_ts=tca_ts,
                min_distance_km=dmin,
                score=score,
                threshold_km=job.threshold_km,
            )


def run_once() -> None:
    """
    Runs a single job and then exits
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
                print(f"Job {job.id} failed; retrying later (attempt {job.attempts}/{job.max_attempts}). Error: {e}")
            else:
                job.status = JobStatus.FAILED.value
                print(f"Job {job.id} failed permanently. Error: {e}")

            db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    run_once()
