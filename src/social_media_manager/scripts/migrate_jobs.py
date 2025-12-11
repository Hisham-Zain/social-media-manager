#!/usr/bin/env python3
"""
Database Migration Script: jobs → jobs_v2

Migrates existing job data from the old raw sqlite3 `jobs` table
to the new SQLAlchemy-managed `jobs_v2` table.

Usage:
    python -m social_media_manager.scripts.migrate_jobs

Requirements:
    - Run this ONCE after upgrading to the new JobQueue implementation
    - Backup your database before running
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger

from social_media_manager.config import config
from social_media_manager.repositories.job_repository import (
    Job,
    JobPriority,
    JobStatus,
    create_job_tables,
)
from social_media_manager.repositories.unit_of_work import get_unit_of_work


def get_old_jobs_path() -> Path:
    """Get path to old jobs.db (raw sqlite3 database)."""
    return Path(config.DATA_DIR) / "jobs.db"


def migrate_jobs() -> None:
    """
    Migrate jobs from old sqlite3 table to new SQLAlchemy table.
    """
    old_db_path = get_old_jobs_path()

    if not old_db_path.exists():
        logger.info("No old jobs database found. Nothing to migrate.")
        return

    # Ensure new tables exist
    create_job_tables(config.DATABASE_URL)

    # Connect to old database
    old_conn = sqlite3.connect(str(old_db_path))
    old_conn.row_factory = sqlite3.Row

    try:
        # Get all jobs from old table
        cursor = old_conn.execute("SELECT * FROM jobs")
        old_jobs = cursor.fetchall()

        if not old_jobs:
            logger.info("No jobs found in old database.")
            return

        logger.info(f"Found {len(old_jobs)} jobs to migrate")

        # Get UnitOfWork for new database
        uow = get_unit_of_work()
        migrated = 0
        skipped = 0

        with uow.begin() as work:
            for row in old_jobs:
                job_id = row["id"]

                # Check if already migrated
                existing = work.jobs.get(job_id)
                if existing:
                    logger.debug(f"Job {job_id[:8]}... already exists, skipping")
                    skipped += 1
                    continue

                # Parse dates
                created_at = None
                if row["created_at"]:
                    try:
                        created_at = datetime.fromisoformat(row["created_at"])
                    except ValueError:
                        created_at = datetime.now()

                started_at = None
                if row["started_at"]:
                    try:
                        started_at = datetime.fromisoformat(row["started_at"])
                    except ValueError:
                        pass

                completed_at = None
                if row["completed_at"]:
                    try:
                        completed_at = datetime.fromisoformat(row["completed_at"])
                    except ValueError:
                        pass

                # Parse payload and result
                payload = {}
                if row["payload"]:
                    try:
                        payload = json.loads(row["payload"])
                    except json.JSONDecodeError:
                        payload = {"raw": row["payload"]}

                result = None
                if row["result"]:
                    try:
                        result = json.loads(row["result"])
                    except json.JSONDecodeError:
                        result = {"raw": row["result"]}

                # Map status
                status_map = {
                    "pending": JobStatus.PENDING,
                    "queued": JobStatus.QUEUED,
                    "running": JobStatus.RUNNING,
                    "completed": JobStatus.COMPLETED,
                    "failed": JobStatus.FAILED,
                    "cancelled": JobStatus.CANCELLED,
                }
                status = status_map.get(row["status"], JobStatus.PENDING)

                # Map priority
                priority_map = {
                    1: JobPriority.LOW,
                    3: JobPriority.LOW,
                    5: JobPriority.NORMAL,
                    7: JobPriority.HIGH,
                    9: JobPriority.CRITICAL,
                    10: JobPriority.CRITICAL,
                }
                priority = priority_map.get(row["priority"], JobPriority.NORMAL)

                # Create new job
                new_job = Job(
                    id=job_id,
                    job_type=row["job_type"],
                    payload=payload,
                    status=status,
                    priority=priority,
                    progress=float(row["progress"] or 0.0),
                    result=result,
                    error=row["error"],
                    created_at=created_at,
                    started_at=started_at,
                    completed_at=completed_at,
                )

                work.jobs.add(new_job)
                migrated += 1

                if migrated % 100 == 0:
                    logger.info(f"Migrated {migrated} jobs...")

        logger.success(f"Migration complete: {migrated} migrated, {skipped} skipped")

        # Optionally rename old database
        backup_path = old_db_path.with_suffix(".db.bak")
        old_db_path.rename(backup_path)
        logger.info(f"Old database renamed to {backup_path}")

    finally:
        old_conn.close()


if __name__ == "__main__":
    logger.info("Starting jobs migration...")
    migrate_jobs()
    logger.info("Done!")
