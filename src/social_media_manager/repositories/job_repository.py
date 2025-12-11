"""
Job Repository - SQLAlchemy-based job storage.

Replaces raw SQL in JobQueue with proper ORM patterns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base

from . import Repository

Base = declarative_base()


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(int, Enum):
    """Job priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20


class JobModel(Base):
    """SQLAlchemy model for jobs table."""

    __tablename__ = "jobs_v2"

    id = Column(String(36), primary_key=True)
    job_type = Column(String(50), nullable=False, index=True)
    payload = Column(Text, nullable=False, default="{}")
    status = Column(String(20), default=JobStatus.PENDING.value, index=True)
    priority = Column(Integer, default=JobPriority.NORMAL.value, index=True)
    progress = Column(Float, default=0.0)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    worker_id = Column(String(50), nullable=True)


@dataclass
class Job:
    """Domain entity representing a background job."""

    id: str
    job_type: str
    payload: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    worker_id: str | None = None


def create_job_tables(db_url: str) -> None:
    """
    Create job tables using SQLAlchemy ORM.

    Args:
        db_url: SQLAlchemy database connection URL.
    """
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)


class JobRepository(Repository[Job, str]):
    """
    Repository for job persistence using SQLAlchemy.

    Replaces raw SQL queries from the original JobQueue implementation.
    """

    def get(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        model = self.session.query(JobModel).filter_by(id=job_id).first()
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Job]:
        """Get all jobs with pagination."""
        models = (
            self.session.query(JobModel)
            .order_by(JobModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def get_by_status(
        self,
        status: JobStatus,
        limit: int = 50,
    ) -> list[Job]:
        """Get jobs filtered by status."""
        models = (
            self.session.query(JobModel)
            .filter_by(status=status.value)
            .order_by(JobModel.priority.desc(), JobModel.created_at.asc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def get_pending(self, limit: int = 10) -> list[Job]:
        """Get pending jobs ordered by priority."""
        models = (
            self.session.query(JobModel)
            .filter(
                JobModel.status.in_([JobStatus.PENDING.value, JobStatus.QUEUED.value])
            )
            .order_by(JobModel.priority.desc(), JobModel.created_at.asc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def add(self, entity: Job) -> Job:
        """Add a new job."""
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()  # Get any DB-generated values
        return entity

    def update(self, entity: Job) -> Job:
        """Update an existing job."""
        model = self.session.query(JobModel).filter_by(id=entity.id).first()
        if model:
            model.status = entity.status.value
            model.progress = entity.progress
            model.result = json.dumps(entity.result) if entity.result else None
            model.error = entity.error
            model.started_at = entity.started_at
            model.completed_at = entity.completed_at
            model.worker_id = entity.worker_id
            self.session.flush()
        return entity

    def delete(self, job_id: str) -> bool:
        """Delete a job by ID."""
        result = self.session.query(JobModel).filter_by(id=job_id).delete()
        return result > 0

    def update_progress(
        self, job_id: str, progress: float, status_msg: str = ""
    ) -> bool:
        """Update job progress."""
        result = (
            self.session.query(JobModel)
            .filter_by(id=job_id)
            .update({"progress": progress})
        )
        return result > 0

    def mark_running(self, job_id: str, worker_id: str | None = None) -> bool:
        """Mark a job as running."""
        result = (
            self.session.query(JobModel)
            .filter_by(id=job_id)
            .filter(
                JobModel.status.in_([JobStatus.PENDING.value, JobStatus.QUEUED.value])
            )
            .update(
                {
                    "status": JobStatus.RUNNING.value,
                    "started_at": datetime.utcnow(),
                    "worker_id": worker_id,
                }
            )
        )
        return result > 0

    def mark_completed(self, job_id: str, result: dict[str, Any] | None = None) -> bool:
        """Mark a job as completed."""
        update_result = (
            self.session.query(JobModel)
            .filter_by(id=job_id)
            .update(
                {
                    "status": JobStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow(),
                    "progress": 100.0,
                    "result": json.dumps(result) if result else None,
                }
            )
        )
        return update_result > 0

    def mark_failed(self, job_id: str, error: str) -> bool:
        """Mark a job as failed."""
        result = (
            self.session.query(JobModel)
            .filter_by(id=job_id)
            .update(
                {
                    "status": JobStatus.FAILED.value,
                    "completed_at": datetime.utcnow(),
                    "error": error,
                }
            )
        )
        return result > 0

    def delete_completed_before(self, cutoff: datetime) -> int:
        """Delete completed and cancelled jobs before cutoff datetime."""
        result = (
            self.session.query(JobModel)
            .filter(
                JobModel.status.in_(
                    [JobStatus.COMPLETED.value, JobStatus.CANCELLED.value]
                )
            )
            .filter(JobModel.completed_at < cutoff)
            .delete(synchronize_session=False)
        )
        return result

    def _to_entity(self, model: JobModel) -> Job:
        """Convert SQLAlchemy model to domain entity."""
        return Job(
            id=model.id,
            job_type=model.job_type,
            payload=json.loads(model.payload) if model.payload else {},
            status=JobStatus(model.status),
            priority=JobPriority(model.priority),
            progress=model.progress or 0.0,
            result=json.loads(model.result) if model.result else None,
            error=model.error,
            created_at=model.created_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            worker_id=model.worker_id,
        )

    def _to_model(self, entity: Job) -> JobModel:
        """Convert domain entity to SQLAlchemy model."""
        return JobModel(
            id=entity.id,
            job_type=entity.job_type,
            payload=json.dumps(entity.payload),
            status=entity.status.value,
            priority=entity.priority.value,
            progress=entity.progress,
            result=json.dumps(entity.result) if entity.result else None,
            error=entity.error,
            created_at=entity.created_at or datetime.utcnow(),
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            worker_id=entity.worker_id,
        )
