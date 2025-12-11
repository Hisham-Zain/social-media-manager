"""
Dependency Injection Container for AgencyOS.

Provides centralized service management and lazy-loading of dependencies.
Enables easy swapping of implementations for testing and configuration.

Usage:
    from social_media_manager.container import get_container

    container = get_container()
    brain = container.brain  # Lazy-loads HybridBrain
    db = container.db        # Returns DatabaseManager
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, TypeVar

from loguru import logger

from .config import Config, config

if TYPE_CHECKING:
    from .ai.brain import HybridBrain
    from .database import DatabaseManager

T = TypeVar("T")


class BrainProtocol(Protocol):
    """Protocol defining the Brain interface for dependency injection."""

    provider: str
    model: str

    def think(
        self,
        prompt: str,
        context: str = "",
        json_mode: bool = False,
    ) -> str:
        """Generate a response using the LLM."""
        ...


@dataclass
class Container:
    """
    Service container for dependency injection.

    Manages the lifecycle of services and provides lazy-loading
    to defer heavy initialization until needed.

    Attributes:
        config: Application configuration.
        _brain: Cached HybridBrain instance.
        _db: Cached DatabaseManager instance.
        _producer: Cached VideoProducer instance.
    """

    config: Config
    _brain: HybridBrain | None = field(default=None, repr=False)
    _db: DatabaseManager | None = field(default=None, repr=False)
    _producer: object | None = field(default=None, repr=False)
    _job_queue: object | None = field(default=None, repr=False)
    _orchestrator: object | None = field(default=None, repr=False)

    @classmethod
    def create(cls, cfg: Config | None = None) -> Container:
        """
        Factory method for creating container with defaults.

        Args:
            cfg: Optional custom configuration. Uses global config if None.

        Returns:
            Configured Container instance.
        """
        return cls(config=cfg or config)

    @property
    def brain(self) -> HybridBrain:
        """
        Get or create the HybridBrain instance (lazy-loaded).

        Returns:
            HybridBrain instance for LLM operations.
        """
        if self._brain is None:
            from .ai.brain import HybridBrain

            self._brain = HybridBrain()
            logger.debug(
                f"Created HybridBrain: {self._brain.provider}/{self._brain.model}"
            )
        return self._brain

    @property
    def db(self) -> DatabaseManager:
        """
        Get or create the DatabaseManager instance (lazy-loaded).

        Returns:
            DatabaseManager for database operations.
        """
        if self._db is None:
            from .database import DatabaseManager

            self._db = DatabaseManager(self.config.DATABASE_URL)
            logger.debug("Created DatabaseManager")
        return self._db

    @property
    def producer(self) -> object:
        """
        Get or create the VideoProducer instance (lazy-loaded).

        Returns:
            VideoProducer for video generation.
        """
        if self._producer is None:
            try:
                from .ai.producer import VideoProducer

                self._producer = VideoProducer()
                logger.debug("Created VideoProducer")
            except ImportError:
                logger.warning("VideoProducer not available")
                self._producer = None  # type: ignore
        return self._producer  # type: ignore

    @property
    def job_queue(self) -> object:
        """
        Get or create the JobQueue instance (lazy-loaded).

        Returns:
            JobQueue for background job processing.
        """
        if self._job_queue is None:
            from .job_queue import JobQueue

            self._job_queue = JobQueue(num_workers=2, auto_start=False)
            logger.debug("Created JobQueue")
        return self._job_queue

    @property
    def orchestrator(self) -> object:
        """
        Get or create the SocialMediaManager (orchestrator) instance.

        Returns:
            SocialMediaManager for workflow orchestration.
        """
        if self._orchestrator is None:
            from .core.orchestrator import SocialMediaManager

            self._orchestrator = SocialMediaManager(
                db=self.db,
                brain=self.brain,
            )
            logger.debug("Created SocialMediaManager orchestrator")
        return self._orchestrator

    def reset(self) -> None:
        """Reset all cached services. Useful for testing."""
        self._brain = None
        self._db = None
        self._producer = None
        self._job_queue = None
        self._orchestrator = None
        logger.debug("Container reset")


# Global container singleton
_container: Container | None = None


def get_container() -> Container:
    """
    Get or create the global service container.

    Returns:
        Global Container instance.
    """
    global _container
    if _container is None:
        _container = Container.create()
    return _container


def reset_container() -> None:
    """Reset the global container. Useful for testing."""
    global _container
    if _container is not None:
        _container.reset()
    _container = None


def set_container(container: Container) -> None:
    """
    Set a custom container. Useful for testing with mocks.

    Args:
        container: Custom Container instance to use globally.
    """
    global _container
    _container = container
