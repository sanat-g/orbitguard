"""
SQLAlchemy ORM models for OrbitGuard

This file defines the database tables and columns used by the app:

- ApproachEvent: ingestion table for NASA/JPL CAD close-approach events.
  Each row is one close approach with a timestamp, miss distance (km), and relative velocity (km/s).

- ScanJob: represents a user-requested scan over a time window and distance threshold.
  Jobs move through a state machine: PENDING → RUNNING → SUCCEEDED/FAILED.

- RiskEvent: the results produced by running a ScanJob.
  Each row records the closest approach distance/time for an object during that scan,
  plus a risk score and an explanation blob for the API/UI.
"""



from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Base class for all ORM models
class Base(DeclarativeBase):
    pass


# Enums (stored as strings)
class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

# Tables
class Object(Base):
    __tablename__ = "objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    object_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    # state at epoch
    epoch_ts: Mapped[int] = mapped_column(Integer, index=True)  # unix seconds
    x_km: Mapped[float] = mapped_column(Float)
    y_km: Mapped[float] = mapped_column(Float)
    z_km: Mapped[float] = mapped_column(Float)

    vx_km_s: Mapped[float] = mapped_column(Float)
    vy_km_s: Mapped[float] = mapped_column(Float)
    vz_km_s: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    start_ts: Mapped[int] = mapped_column(Integer, index=True)
    end_ts: Mapped[int] = mapped_column(Integer, index=True)
    threshold_km: Mapped[float] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String, default=JobStatus.PENDING.value, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_id: Mapped[int] = mapped_column(ForeignKey("scan_jobs.id"), index=True)
    object_id: Mapped[str] = mapped_column(String, index=True)  # keep simple for MVP

    min_distance_km: Mapped[float] = mapped_column(Float)
    tca_ts: Mapped[int] = mapped_column(Integer, index=True)  # time of closest approach
    risk_score: Mapped[float] = mapped_column(Float)

    explanation_json: Mapped[str] = mapped_column(Text)  # store JSON as text for MVP

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

#Data ingested from NASA API propagated into database
class ApproachEvent(Base):
    __tablename__ = "approach_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Object designation/id (CAD field: des)
    object_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Approach time (CAD field: cd converted to unix seconds)
    approach_ts: Mapped[int] = mapped_column(Integer, index=True)

    # Miss distance in km (CAD field: dist in AU -> km)
    miss_distance_km: Mapped[float] = mapped_column(Float, index=True)

    # Relative velocity in km/s (CAD field: v_rel)
    v_rel_km_s: Mapped[float] = mapped_column(Float)

    source: Mapped[str] = mapped_column(String, default="NASA_JPL_CAD")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
