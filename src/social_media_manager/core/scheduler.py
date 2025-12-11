"""
Content Scheduler for AgencyOS.

Schedule content for future publishing with cron-like scheduling.
"""

import json
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Literal

from loguru import logger

from ..config import config


@dataclass
class ScheduledTask:
    """A scheduled task."""

    id: str
    name: str
    task_type: Literal["publish", "generate", "custom"]
    scheduled_time: str  # ISO format
    payload: dict[str, Any]

    # Status
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = (
        "pending"
    )
    result: dict[str, Any] | None = None
    error: str | None = None

    # Recurrence
    recurrence: str | None = None  # "daily", "weekly", "monthly", or cron
    next_run: str | None = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "scheduled_time": self.scheduled_time,
            "payload": self.payload,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "recurrence": self.recurrence,
            "next_run": self.next_run,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduledTask":
        return cls(**data)


class Scheduler:
    """
    Content scheduler with recurring task support.

    Example:
        scheduler = Scheduler()

        # Schedule a one-time task
        scheduler.schedule(
            name="Publish Video",
            task_type="publish",
            scheduled_time=datetime.now() + timedelta(hours=2),
            payload={
                "content_id": "video_123",
                "platform": "youtube",
            }
        )

        # Schedule recurring task
        scheduler.schedule(
            name="Weekly Digest",
            task_type="generate",
            scheduled_time=datetime.now(),
            payload={"type": "weekly_digest"},
            recurrence="weekly",
        )

        # Register handler
        @scheduler.on_task("publish")
        def handle_publish(payload):
            print(f"Publishing: {payload}")

        # Start scheduler (in background)
        scheduler.start()
    """

    CHECK_INTERVAL = 60  # Check every minute

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (config.BASE_DIR / "scheduler")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._tasks: dict[str, ScheduledTask] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._running = False
        self._thread: threading.Thread | None = None

        self._load()
        logger.info(f"📅 Scheduler initialized ({len(self._tasks)} tasks)")

    def _load(self):
        """Load tasks from disk."""
        tasks_file = self.data_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file) as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = ScheduledTask.from_dict(task_data)
                        self._tasks[task.id] = task
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse tasks.json: {e}")
            except FileNotFoundError:
                pass  # Expected on first run
            except OSError as e:
                logger.warning(f"Failed to load tasks (I/O): {e}")

    def _save(self):
        """Save tasks to disk."""
        tasks_file = self.data_dir / "tasks.json"
        with open(tasks_file, "w") as f:
            json.dump(
                {"tasks": [t.to_dict() for t in self._tasks.values()]}, f, indent=2
            )

    def schedule(
        self,
        name: str,
        task_type: Literal["publish", "generate", "custom"],
        scheduled_time: datetime | str,
        payload: dict[str, Any],
        recurrence: str | None = None,
    ) -> ScheduledTask:
        """
        Schedule a new task.

        Args:
            name: Task name.
            task_type: Type of task.
            scheduled_time: When to run (datetime or ISO string).
            payload: Task data.
            recurrence: Optional recurrence ("daily", "weekly", "monthly").

        Returns:
            Created ScheduledTask.
        """
        import hashlib

        task_id = hashlib.md5(
            f"{name}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        if isinstance(scheduled_time, datetime):
            scheduled_time = scheduled_time.isoformat()

        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=task_type,
            scheduled_time=scheduled_time,
            payload=payload,
            recurrence=recurrence,
        )

        self._tasks[task_id] = task
        self._save()

        logger.info(f"📅 Scheduled: {name} for {scheduled_time}")
        return task

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self._tasks.get(task_id)
        if task and task.status == "pending":
            task.status = "cancelled"
            self._save()
            logger.info(f"❌ Cancelled task: {task.name}")
            return True
        return False

    def reschedule(
        self,
        task_id: str,
        new_time: datetime | str,
    ) -> ScheduledTask | None:
        """Reschedule a task to a new time."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        if isinstance(new_time, datetime):
            new_time = new_time.isoformat()

        task.scheduled_time = new_time
        task.status = "pending"
        self._save()

        logger.info(f"🔄 Rescheduled: {task.name} to {new_time}")
        return task

    def list_tasks(
        self,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[ScheduledTask]:
        """List scheduled tasks."""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        # Sort by scheduled time
        tasks.sort(key=lambda t: t.scheduled_time)

        return tasks

    def get_upcoming(self, hours: int = 24) -> list[ScheduledTask]:
        """Get tasks scheduled in the next N hours."""
        cutoff = datetime.now() + timedelta(hours=hours)

        return [
            t
            for t in self._tasks.values()
            if t.status == "pending"
            and datetime.fromisoformat(t.scheduled_time) <= cutoff
        ]

    def on_task(self, task_type: str) -> Callable[..., Any]:
        """
        Decorator to register a task handler.

        Example:
            @scheduler.on_task("publish")
            def handle_publish(payload):
                # Publish content
                pass
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._handlers[task_type] = func
            return func

        return decorator

    def register_handler(
        self,
        task_type: str,
        handler: Callable[..., Any],
    ):
        """Register a task handler programmatically."""
        self._handlers[task_type] = handler

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        task.status = "running"
        self._save()

        logger.info(f"▶️ Executing task: {task.name}")

        try:
            handler = self._handlers.get(task.task_type)

            if handler:
                result = handler(task.payload)
                task.result = result if isinstance(result, dict) else {"success": True}
                task.status = "completed"
            else:
                logger.warning(f"No handler for task type: {task.task_type}")
                task.status = "failed"
                task.error = f"No handler for task type: {task.task_type}"

        except KeyError as e:
            logger.error(f"❌ Task failed (missing key): {task.name} - {e}")
            task.status = "failed"
            task.error = f"Missing required key: {e}"
        except TypeError as e:
            logger.error(f"❌ Task failed (type error): {task.name} - {e}")
            task.status = "failed"
            task.error = str(e)
        except Exception as e:
            # Log full traceback for unexpected errors
            logger.error(f"❌ Task failed ({type(e).__name__}): {task.name} - {e}")
            logger.error(traceback.format_exc())
            task.status = "failed"
            task.error = f"{type(e).__name__}: {e}"

        task.completed_at = datetime.now().isoformat()

        # Handle recurrence
        if task.status == "completed" and task.recurrence:
            self._schedule_next_occurrence(task)

        self._save()

    def _schedule_next_occurrence(self, task: ScheduledTask):
        """Schedule the next occurrence of a recurring task."""
        current = datetime.fromisoformat(task.scheduled_time)

        if task.recurrence == "daily":
            next_time = current + timedelta(days=1)
        elif task.recurrence == "weekly":
            next_time = current + timedelta(weeks=1)
        elif task.recurrence == "monthly":
            next_time = current + timedelta(days=30)
        else:
            return

        task.next_run = next_time.isoformat()

        # Create new task for next occurrence
        self.schedule(
            name=task.name,
            task_type=task.task_type,
            scheduled_time=next_time,
            payload=task.payload,
            recurrence=task.recurrence,
        )

    def _check_and_run(self):
        """Check for due tasks and execute them."""
        now = datetime.now()

        for task in list(self._tasks.values()):
            if task.status != "pending":
                continue

            scheduled = datetime.fromisoformat(task.scheduled_time)

            if scheduled <= now:
                self._execute_task(task)

    def start(self):
        """Start the scheduler in background."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info("📅 Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

        logger.info("📅 Scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                self._check_and_run()
            except KeyboardInterrupt:
                logger.info("Scheduler received shutdown signal")
                break
            except OSError as e:
                logger.error(f"Scheduler I/O error: {e}")
                logger.debug(traceback.format_exc())
            except Exception as e:
                # Log full traceback but keep running
                logger.error(f"Scheduler error ({type(e).__name__}): {e}")
                logger.error(traceback.format_exc())

            time.sleep(self.CHECK_INTERVAL)

    def run_now(self, task_id: str) -> bool:
        """Manually trigger a task immediately."""
        task = self._tasks.get(task_id)
        if task and task.status == "pending":
            self._execute_task(task)
            return True
        return False


# Singleton
_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler:
    """Get the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


def schedule_task(
    name: str,
    task_type: str,
    scheduled_time: datetime,
    payload: dict[str, Any],
    recurrence: str | None = None,
) -> ScheduledTask:
    """Quick function to schedule a task."""
    return get_scheduler().schedule(
        name=name,
        task_type=task_type,
        scheduled_time=scheduled_time,
        payload=payload,
        recurrence=recurrence,
    )
