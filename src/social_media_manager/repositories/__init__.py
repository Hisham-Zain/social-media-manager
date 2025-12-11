"""
Repository Pattern - Base Classes.

Abstract repository interfaces for data access layer.
Provides consistent data access across the application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")
ID = TypeVar("ID", str, int)


class Repository(ABC, Generic[T, ID]):
    """
    Abstract base repository defining standard CRUD operations.

    All concrete repositories should inherit from this class
    to ensure consistent data access patterns.

    Type Parameters:
        T: The entity type this repository manages.
        ID: The type of the entity's identifier.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize repository with a database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self.session = session

    @abstractmethod
    def get(self, entity_id: ID) -> T | None:
        """
        Get an entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        ...

    @abstractmethod
    def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """
        Get all entities with pagination.

        Args:
            limit: Maximum number of entities to return.
            offset: Number of entities to skip.

        Returns:
            List of entities.
        """
        ...

    @abstractmethod
    def add(self, entity: T) -> T:
        """
        Add a new entity.

        Args:
            entity: The entity to add.

        Returns:
            The added entity (with any generated fields populated).
        """
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update an existing entity.

        Args:
            entity: The entity with updated values.

        Returns:
            The updated entity.
        """
        ...

    @abstractmethod
    def delete(self, entity_id: ID) -> bool:
        """
        Delete an entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity to delete.

        Returns:
            True if deleted, False if not found.
        """
        ...
