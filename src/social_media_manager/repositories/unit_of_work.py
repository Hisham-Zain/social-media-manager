"""
Unit of Work Pattern - Transaction Management.

Provides atomic transaction handling across multiple repositories.
Ensures database consistency by committing or rolling back together.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .job_repository import JobRepository

if TYPE_CHECKING:
    pass


class _UnitOfWorkContext:
    """
    Context for a single unit of work transaction.

    This is a thread-local context that holds the session and repositories
    for a single transaction. Each call to UnitOfWork.begin() creates a new
    instance to ensure thread-safety.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self.jobs = JobRepository(session)

    def commit(self) -> None:
        """Manually commit the current transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Manually rollback the current transaction."""
        self._session.rollback()


class UnitOfWork:
    """
    Manages database transactions across repositories.

    Ensures all operations within a unit of work are committed
    or rolled back together, maintaining data consistency.

    Thread-safe: Each call to begin() creates an isolated session context.

    Usage:
        uow = UnitOfWork(db_url)
        with uow.begin() as work:
            job = Job(id="123", job_type="render", payload={})
            work.jobs.add(job)
            # Auto-commits on exit, rolls back on exception
    """

    def __init__(self, db_url: str) -> None:
        """
        Initialize Unit of Work with database URL.

        Args:
            db_url: SQLAlchemy database connection URL.
        """
        self._engine = create_engine(db_url)
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )

    @contextmanager
    def begin(self) -> Generator[_UnitOfWorkContext, None, None]:
        """
        Begin a new unit of work transaction.

        Each call creates an isolated session context, making this method
        thread-safe for concurrent use by multiple worker threads.

        Yields:
            UnitOfWorkContext with active session and repositories.

        Raises:
            Exception: Re-raises any exception after rollback.
        """
        # Create a new session for this context (thread-safe)
        session = self._session_factory()
        context = _UnitOfWorkContext(session)
        try:
            yield context

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Unit of work rolled back: {e}")
            raise
        finally:
            session.close()


# Convenience function
_uow_instance: UnitOfWork | None = None


def get_unit_of_work(db_url: str | None = None) -> UnitOfWork:
    """
    Get or create a Unit of Work instance.

    Args:
        db_url: Database URL. Uses config default if None.

    Returns:
        UnitOfWork instance.
    """
    global _uow_instance
    if _uow_instance is None:
        if db_url is None:
            from ..config import config

            db_url = config.DATABASE_URL
        _uow_instance = UnitOfWork(db_url)
    return _uow_instance
