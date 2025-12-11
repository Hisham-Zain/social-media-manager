"""
Background Job Queue for AgencyOS.

Decouples heavy processing (video rendering, AI generation) from the UI
to prevent freezing and enable batch processing.

Features:
- SQLite-backed persistent job queue
- Background worker threads
- Progress tracking and status updates
- Job prioritization
- Automatic retries
"""

import json
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import Queue
from typing import Any, Callable
from uuid import uuid4

from loguru import logger

from .config import config
from .repositories.job_repository import (
    create_job_tables,
)
from .repositories.unit_of_work import get_unit_of_work


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


@dataclass
class Job:
    """Represents a background job."""

    id: str
    job_type: str
    payload: dict
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    progress: float = 0.0
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    retries: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "payload": json.dumps(self.payload),
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": self.progress,
            "result": json.dumps(self.result) if self.result else None,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retries": self.retries,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            job_type=data["job_type"],
            payload=json.loads(data["payload"])
            if isinstance(data["payload"], str)
            else data["payload"],
            status=JobStatus(data["status"]),
            priority=JobPriority(data["priority"]),
            progress=data["progress"],
            result=json.loads(data["result"]) if data.get("result") else None,
            error=data.get("error"),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", 3),
        )


class JobQueue:
    """
    SQLite-backed job queue with background workers.

    Usage:
        queue = JobQueue()
        queue.start()

        # Submit a job
        job_id = queue.submit("video_render", {"script": "...", "avatar": "..."})

        # Check status
        job = queue.get_job(job_id)
        print(f"Status: {job.status}, Progress: {job.progress}%")

        # Stop workers
        queue.stop()
    """

    # Registry of job handlers
    _handlers: dict[str, Callable] = {}

    def __init__(
        self,
        db_path: Path | None = None,
        num_workers: int = 2,
        auto_start: bool = False,
    ):
        """
        Initialize job queue.

        Args:
            db_path: Path to SQLite database for job storage (legacy, ignored if using ORM).
            num_workers: Number of background worker threads.
            auto_start: Start workers automatically.
        """
        # Use UnitOfWork for database operations
        self._uow = get_unit_of_work()

        # Initialize ORM tables
        self._init_db()

        self.num_workers = num_workers
        self._workers: list[threading.Thread] = []
        self._stop_event = threading.Event()
        self._job_queue: Queue[str] = Queue()

        # Register built-in handlers
        self._register_builtin_handlers()

        if auto_start:
            self.start()

        logger.info(f"📋 JobQueue initialized (workers: {num_workers})")

    def _init_db(self) -> None:
        """Initialize database tables via SQLAlchemy ORM."""
        # Create tables using the repository's Base metadata
        create_job_tables(config.DATABASE_URL)

    def _register_builtin_handlers(self):
        """Register built-in job handlers."""
        # Video production
        self.register_handler("video_produce", self._handle_video_produce)
        self.register_handler("video_render", self._handle_video_render)
        self.register_handler("video_process", self._handle_video_process)

        # AI generation
        self.register_handler("music_compose", self._handle_music_compose)
        self.register_handler("avatar_generate", self._handle_avatar_generate)
        self.register_handler("thumbnail_generate", self._handle_thumbnail_generate)
        self.register_handler("ab_test", self._handle_ab_test)
        self.register_handler("hook_generate", self._handle_hook_generate)
        self.register_handler("global_content", self._handle_global_content)

        # Processing
        self.register_handler("upscale_image", self._handle_upscale_image)
        self.register_handler("remove_background", self._handle_remove_background)
        self.register_handler("batch_process", self._handle_batch_process)

        # Trend scanning
        self.register_handler("trend_scan", self._handle_trend_scan)
        self.register_handler("scan_trends", self._handle_trend_scan)  # Alias
        self.register_handler("forecast_trends", self._handle_forecast_trends)

        # Autonomy & Consensus (Phase 1 & 3)
        self.register_handler("autonomy_cycle", self._handle_autonomy_cycle)
        self.register_handler("consensus_refine", self._handle_consensus_refine)

    @classmethod
    def register_handler(cls, job_type: str, handler: Callable):
        """Register a job handler function."""
        cls._handlers[job_type] = handler
        logger.debug(f"Registered handler: {job_type}")

    def submit(
        self,
        job_type: str,
        payload: dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
    ) -> str:
        """
        Submit a new job to the queue.

        Args:
            job_type: Type of job (must have registered handler).
            payload: Job parameters.
            priority: Job priority.

        Returns:
            Job ID.
        """
        from .repositories.job_repository import Job as RepoJob
        from .repositories.job_repository import JobPriority as RepoPriority
        from .repositories.job_repository import JobStatus as RepoStatus

        job_id = str(uuid4())

        # Create repository job entity
        repo_job = RepoJob(
            id=job_id,
            job_type=job_type,
            payload=payload,
            status=RepoStatus.QUEUED,
            priority=RepoPriority(priority.value),
            progress=0.0,
        )

        # Store in database via UnitOfWork
        with self._uow.begin() as uow:
            uow.jobs.add(repo_job)

        # Add to in-memory queue for immediate processing
        self._job_queue.put(job_id)

        logger.info(f"📥 Job submitted: {job_id[:8]}... ({job_type})")
        return job_id

    def get_job(self, job_id: str) -> Job | None:
        """Get job by ID."""
        with self._uow.begin() as uow:
            repo_job = uow.jobs.get(job_id)
            if repo_job:
                # Convert repository Job to local Job
                return Job(
                    id=repo_job.id,
                    job_type=repo_job.job_type,
                    payload=repo_job.payload,
                    status=JobStatus(repo_job.status.value),
                    priority=JobPriority(repo_job.priority.value),
                    progress=repo_job.progress,
                    result=repo_job.result,
                    error=repo_job.error,
                    created_at=repo_job.created_at.isoformat()
                    if repo_job.created_at
                    else None,
                    started_at=repo_job.started_at.isoformat()
                    if repo_job.started_at
                    else None,
                    completed_at=repo_job.completed_at.isoformat()
                    if repo_job.completed_at
                    else None,
                )
        return None

    def get_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> list[Job]:
        """Get jobs with optional status filter."""
        from .repositories.job_repository import JobStatus as RepoStatus

        with self._uow.begin() as uow:
            if status:
                repo_jobs = uow.jobs.get_by_status(
                    RepoStatus(status.value), limit=limit
                )
            else:
                repo_jobs = uow.jobs.get_all(limit=limit)

            # Convert to local Job format
            return [
                Job(
                    id=j.id,
                    job_type=j.job_type,
                    payload=j.payload,
                    status=JobStatus(j.status.value),
                    priority=JobPriority(j.priority.value),
                    progress=j.progress,
                    result=j.result,
                    error=j.error,
                    created_at=j.created_at.isoformat() if j.created_at else None,
                    started_at=j.started_at.isoformat() if j.started_at else None,
                    completed_at=j.completed_at.isoformat() if j.completed_at else None,
                )
                for j in repo_jobs
            ]

    def get_pending_jobs(self) -> list[Job]:
        """Get all pending/queued jobs."""
        return self.get_jobs(JobStatus.QUEUED) + self.get_jobs(JobStatus.PENDING)

    def update_job(
        self,
        job_id: str,
        status: JobStatus | None = None,
        progress: float | None = None,
        result: Any | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status and progress."""
        from .repositories.job_repository import JobStatus as RepoStatus

        with self._uow.begin() as uow:
            repo_job = uow.jobs.get(job_id)
            if repo_job:
                if status is not None:
                    repo_job.status = RepoStatus(status.value)
                    if status == JobStatus.RUNNING:
                        uow.jobs.mark_running(job_id)
                    elif status == JobStatus.COMPLETED:
                        uow.jobs.mark_completed(job_id, result)
                    elif status == JobStatus.FAILED:
                        uow.jobs.mark_failed(job_id, error or "Unknown error")
                    else:
                        uow.jobs.update(repo_job)
                if progress is not None:
                    repo_job.progress = progress
                    uow.jobs.update(repo_job)
                if result is not None and status != JobStatus.COMPLETED:
                    repo_job.result = result
                    uow.jobs.update(repo_job)
                if error is not None and status != JobStatus.FAILED:
                    repo_job.error = error
                    uow.jobs.update(repo_job)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending/queued job."""
        job = self.get_job(job_id)
        if job and job.status in (JobStatus.PENDING, JobStatus.QUEUED):
            self.update_job(job_id, status=JobStatus.CANCELLED)
            logger.info(f"❌ Job cancelled: {job_id[:8]}...")
            return True
        return False

    def retry_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        from .repositories.job_repository import JobStatus as RepoStatus

        job = self.get_job(job_id)
        if job and job.status == JobStatus.FAILED and job.retries < job.max_retries:
            with self._uow.begin() as uow:
                repo_job = uow.jobs.get(job_id)
                if repo_job:
                    repo_job.status = RepoStatus.QUEUED
                    repo_job.error = None
                    uow.jobs.update(repo_job)
            self._job_queue.put(job_id)
            logger.info(f"🔄 Job retry: {job_id[:8]}... (attempt {job.retries + 1})")
            return True
        return False

    def clear_completed(self, older_than_hours: int = 24) -> None:
        """Clear completed jobs older than specified hours."""

        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        with self._uow.begin() as uow:
            uow.jobs.delete_completed_before(cutoff)

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a specific job from the database.

        Args:
            job_id: ID of the job to delete.

        Returns:
            True if job was deleted, False otherwise.
        """
        with self._uow.begin() as uow:
            deleted = uow.jobs.delete(job_id)
            if deleted:
                logger.info(f"🗑️ Job deleted: {job_id[:8]}...")
            return deleted

    def clear_failed(self) -> int:
        """
        Clear all failed jobs from the queue.

        Returns:
            Number of jobs deleted.
        """
        from .repositories.job_repository import JobStatus as RepoStatus

        count = 0
        with self._uow.begin() as uow:
            failed_jobs = uow.jobs.get_by_status(RepoStatus.FAILED, limit=1000)
            for job in failed_jobs:
                if uow.jobs.delete(job.id):
                    count += 1

        if count > 0:
            logger.info(f"🧹 Cleared {count} failed jobs")
        return count

    def start(self):
        """Start background worker threads."""
        if self._workers:
            logger.warning("Workers already running")
            return

        self._stop_event.clear()

        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop, name=f"JobWorker-{i}", daemon=True
            )
            worker.start()
            self._workers.append(worker)

        logger.info(f"🚀 Started {self.num_workers} background workers")

    def stop(self, wait: bool = True, timeout: float = 30.0):
        """Stop background workers."""
        self._stop_event.set()

        if wait:
            for worker in self._workers:
                worker.join(timeout=timeout / len(self._workers))

        self._workers.clear()
        logger.info("🛑 Background workers stopped")

    def _worker_loop(self):
        """Main worker loop."""
        while not self._stop_event.is_set():
            try:
                # Check for queued jobs in database
                pending = self.get_jobs(JobStatus.QUEUED, limit=1)

                if pending:
                    job = pending[0]
                    self._process_job(job)
                else:
                    # Wait for new jobs
                    time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Worker received shutdown signal")
                break
            except OSError as e:
                # Database or file system error
                logger.error(f"Worker I/O error: {e}")
                logger.debug(traceback.format_exc())
                time.sleep(5)
            except Exception as e:
                # Log full traceback for debugging, don't swallow silently
                logger.error(f"Worker unexpected error ({type(e).__name__}): {e}")
                logger.debug(traceback.format_exc())
                time.sleep(5)

    def _process_job(self, job: Job):
        """Process a single job."""
        handler = self._handlers.get(job.job_type)

        if not handler:
            self.update_job(
                job.id, status=JobStatus.FAILED, error=f"No handler for: {job.job_type}"
            )
            return

        logger.info(f"⚙️ Processing job: {job.id[:8]}... ({job.job_type})")
        self.update_job(job.id, status=JobStatus.RUNNING, progress=0.0)

        try:
            # Create progress callback
            def update_progress(progress: float, message: str = ""):
                self.update_job(job.id, progress=progress)
                if message:
                    logger.debug(f"Job {job.id[:8]}: {message}")

            # Run handler
            result = handler(job.payload, update_progress)

            self.update_job(
                job.id, status=JobStatus.COMPLETED, progress=100.0, result=result
            )
            logger.info(f"✅ Job completed: {job.id[:8]}...")

        except FileNotFoundError as e:
            error_msg = f"FileNotFoundError: {e}"
            logger.error(f"❌ Job failed (file missing): {job.id[:8]}... - {error_msg}")
            logger.debug(traceback.format_exc())
            self.update_job(job.id, status=JobStatus.FAILED, error=error_msg)
        except OSError as e:
            error_msg = f"OSError: {e}"
            logger.error(f"❌ Job failed (I/O): {job.id[:8]}... - {error_msg}")
            logger.debug(traceback.format_exc())
            self.update_job(job.id, status=JobStatus.FAILED, error=error_msg)
            # Retry on I/O errors (transient)
            if job.retries < job.max_retries:
                time.sleep(5)
                self.retry_job(job.id)
        except ValueError as e:
            error_msg = f"ValueError: {e}"
            logger.error(f"❌ Job failed (bad input): {job.id[:8]}... - {error_msg}")
            logger.debug(traceback.format_exc())
            self.update_job(job.id, status=JobStatus.FAILED, error=error_msg)
        except Exception as e:
            # Catch-all with full traceback for debugging
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ Job failed (unexpected): {job.id[:8]}... - {error_msg}")
            logger.error(traceback.format_exc())  # Log full traceback at ERROR level
            self.update_job(job.id, status=JobStatus.FAILED, error=error_msg)
            # Auto-retry if applicable
            if job.retries < job.max_retries:
                time.sleep(5)
                self.retry_job(job.id)

    # === Built-in Job Handlers ===

    def _handle_video_produce(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle video production job."""
        from .ai.producer import VideoProducer

        producer = VideoProducer()
        progress_cb(10, "Initializing producer")

        result = producer.produce(
            script=payload["script"],
            avatar_image=payload["avatar_image"],
            name=payload.get("name", "Untitled"),
            platform=payload.get("platform", "youtube"),
            voice=payload.get("voice", "en-US-AriaNeural"),
            add_music=payload.get("add_music", True),
        )

        progress_cb(100, "Video produced")
        return {"video_path": result}

    def _handle_video_render(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle video rendering job via Orchestrator."""
        from .container import get_container

        container = get_container()
        manager = container.orchestrator
        progress_cb(10, "Initializing workflow...")

        # Extract arguments from the ticket (payload)
        video_path = payload.get("video_path")
        platforms = payload.get("platforms", ["youtube"])
        client_name = payload.get("client_name", "General")

        progress_cb(20, "Starting processing pipeline...")

        result = manager.process_video(
            raw_path=video_path,
            platforms=platforms,
            client_name=client_name,
        )

        progress_cb(100, "Rendering complete")
        return {"output": result}

    def _handle_music_compose(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle music composition job."""
        from .ai.composer import MusicComposer

        progress_cb(10, "Loading MusicGen model")
        composer = MusicComposer(model="small")

        progress_cb(30, "Composing music")
        if payload.get("style"):
            result = composer.compose_with_style(
                payload["style"], payload.get("duration", 30)
            )
        else:
            result = composer.compose(
                payload.get("prompt", "background music"), payload.get("duration", 30)
            )

        progress_cb(100, "Music composed")
        return {"music_path": result}

    def _handle_avatar_generate(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle avatar generation job."""
        from .ai.avatar import AvatarEngine

        progress_cb(10, "Initializing SadTalker")
        engine = AvatarEngine(size=256)

        progress_cb(30, "Generating talking head")
        result = engine.generate(
            image_path=payload["image_path"],
            audio_path=payload["audio_path"],
            preset=payload.get("preset", "news_anchor"),
        )

        progress_cb(100, "Avatar generated")
        return {"video_path": result}

    def _handle_thumbnail_generate(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle thumbnail generation job."""
        from .ai.studio import GenerativeStudio

        progress_cb(20, "Generating thumbnail")
        studio = GenerativeStudio()

        result = studio.generate_image(
            prompt=payload["prompt"],
            size=payload.get("size", "1792x1024"),
        )

        progress_cb(100, "Thumbnail generated")
        return {"thumbnail_path": result}

    def _handle_ab_test(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle A/B test generation job."""
        from .ai.ab_optimizer import ABOptimizer

        progress_cb(10, "Initializing optimizer")
        optimizer = ABOptimizer()

        progress_cb(30, "Generating variants")
        tests = optimizer.generate_complete_test(
            topic=payload["topic"],
            platform=payload.get("platform", "youtube"),
            include_titles=payload.get("include_titles", True),
            include_thumbnails=payload.get("include_thumbnails", False),
            include_hooks=payload.get("include_hooks", True),
        )

        progress_cb(80, "Getting recommendations")
        recommendations = optimizer.get_recommendations(tests)

        progress_cb(100, "A/B test complete")
        return {
            "tests": {k: len(v.variants) for k, v in tests.items()},
            "recommendations": recommendations,
        }

    def _handle_upscale_image(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle image upscaling job."""
        from .ai.upscaler import ImageUpscaler

        progress_cb(10, "Loading Real-ESRGAN")
        upscaler = ImageUpscaler(model=payload.get("model", "x4plus"))

        progress_cb(30, "Upscaling image")
        result = upscaler.upscale(
            payload["image_path"],
            scale=payload.get("scale", 4),
        )

        progress_cb(100, "Upscaling complete")
        return {"output_path": result}

    def _handle_remove_background(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle background removal job."""
        from .ai.background_remover import BackgroundRemover

        progress_cb(20, "Removing background")
        remover = BackgroundRemover()

        result = remover.remove(payload["image_path"])

        progress_cb(100, "Background removed")
        return {"output_path": result}

    def _handle_batch_process(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle batch processing job."""
        items = payload.get("items", [])
        job_type = payload.get("job_type")
        results = []

        for i, item in enumerate(items):
            progress = ((i + 1) / len(items)) * 100
            progress_cb(progress, f"Processing {i + 1}/{len(items)}")

            # Submit sub-job (synchronously for batch)
            handler = self._handlers.get(job_type)
            if handler:
                result = handler(item, lambda p, m="": None)
                results.append(result)

        return {"results": results, "count": len(results)}

    def _handle_video_process(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle full video processing pipeline."""
        from .container import get_container

        progress_cb(5, "Initializing orchestrator")
        manager = get_container().orchestrator

        progress_cb(20, "Processing video")
        result = manager.process_video(
            raw_path=payload["video_path"],
            platforms=[payload.get("platform", "youtube")],
            client_name=payload.get("client_name"),
            options=payload.get("options"),
        )

        progress_cb(100, "Video processed")
        return result.to_dict() if hasattr(result, "to_dict") else result

    def _handle_hook_generate(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle viral hook generation."""
        from .container import get_container

        progress_cb(10, "Initializing AI")
        brain = get_container().brain

        progress_cb(30, "Generating hooks")
        result = brain.generate_viral_hooks(payload["topic"])

        progress_cb(100, "Hooks generated")
        return {"hooks": result}

    def _handle_global_content(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle multi-language content generation."""
        from .container import get_container

        progress_cb(5, "Initializing orchestrator")
        manager = get_container().orchestrator

        progress_cb(20, "Creating global content")
        result = manager.create_global_content(
            topic=payload["topic"],
            languages=payload["languages"],
        )

        progress_cb(100, "Global content created")
        return {"assets": result}

    def _handle_trend_scan(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle trend scanning job."""
        from .ai.radar import TrendRadar

        progress_cb(10, "Initializing trend radar")
        radar = TrendRadar()

        topic = payload.get("topic", "Tech")
        progress_cb(30, f"Scanning trends for '{topic}'")

        result = radar.check_trends(topic)

        progress_cb(100, "Trend scan complete")
        return (
            {"trends": result}
            if result
            else {"trends": None, "error": "No trends found"}
        )

    def _handle_forecast_trends(self, payload: dict, progress_cb: Callable) -> dict:
        """Handle trend forecasting job."""
        from .ai.forecaster import TrendForecaster
        from .container import get_container

        progress_cb(10, "Initializing forecaster")
        db = get_container().db
        forecaster = TrendForecaster(db_manager=db)

        progress_cb(30, "Forecasting trends")

        result = forecaster.predict_next_week()

        progress_cb(100, "Forecast complete")
        return {"prediction": result}

    def _handle_autonomy_cycle(
        self, payload: dict[str, Any], progress_cb: Callable[[float, str], None]
    ) -> dict[str, Any]:
        """Handle autonomous daily cycle job."""
        from .container import get_container
        from .core.autonomy import AutonomyEngine

        progress_cb(10, "Initializing autonomy engine")
        container = get_container()
        engine = AutonomyEngine(
            db=container.db,
            brain=container.brain,
            client_niche=payload.get("niche", "Tech"),
        )

        progress_cb(20, "Running daily cycle")
        result = engine.run_daily_cycle(
            progress_callback=lambda p, m: progress_cb(20 + p * 0.7, m)
        )

        progress_cb(100, "Autonomy cycle complete")
        return result

    def _handle_consensus_refine(
        self, payload: dict[str, Any], progress_cb: Callable[[float, str], None]
    ) -> dict[str, Any]:
        """Handle consensus-based content refinement job."""
        from .ai.consensus import ConsensusEngine
        from .container import get_container

        progress_cb(10, "Initializing consensus engine")
        brain = get_container().brain
        engine = ConsensusEngine(
            brain=brain,
            max_rounds=payload.get("max_rounds", 3),
        )

        progress_cb(20, "Running refinement debate")
        draft = payload.get("draft", "")
        persona = payload.get("persona", "Gen Z Hater")

        result = engine.refine_script(draft, persona=persona)

        progress_cb(100, "Consensus refinement complete")
        return {
            "original": result.original,
            "final_version": result.final_version,
            "rounds": len(result.rounds),
            "converged": result.converged,
            "safety_approved": result.safety_approved,
        }


# Global queue instance
_queue: JobQueue | None = None


def get_queue() -> JobQueue:
    """Get or create the global job queue."""
    global _queue
    if _queue is None:
        _queue = JobQueue(num_workers=2, auto_start=True)
    return _queue


def submit_job(
    job_type: str, payload: dict, priority: JobPriority = JobPriority.NORMAL
) -> str:
    """Convenience function to submit a job."""
    return get_queue().submit(job_type, payload, priority)


def get_job_status(job_id: str) -> dict | None:
    """Convenience function to get job status."""
    job = get_queue().get_job(job_id)
    if job:
        return {
            "id": job.id,
            "type": job.job_type,
            "status": job.status.value,
            "progress": job.progress,
            "result": job.result,
            "error": job.error,
        }
    return None
