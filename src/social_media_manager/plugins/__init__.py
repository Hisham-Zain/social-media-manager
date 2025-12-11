"""
Plugin Architecture - Base Classes.

Defines the ToolPlugin protocol for AI tools extensibility.
Enables dynamic loading of tools without modifying core code.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""

    name: str
    description: str
    icon: str
    category: str  # "writing", "audio", "visual", "video", "research"
    version: str = "1.0.0"
    author: str = "AgencyOS"


@runtime_checkable
class ToolPlugin(Protocol):
    """
    Protocol defining the AI tool plugin interface.

    All plugins must implement this protocol to be loaded
    by the plugin manager and displayed in the AI Tools view.

    Attributes:
        metadata: Plugin metadata (name, icon, category, etc.)

    Example:
        class MyToolPlugin:
            metadata = PluginMetadata(
                name="My Tool",
                description="Does something cool",
                icon="🔧",
                category="writing",
            )

            def get_widget(self) -> QWidget:
                return MyToolWidget()

            def execute(self, **kwargs) -> dict:
                return {"result": "success"}
    """

    metadata: PluginMetadata

    @abstractmethod
    def get_widget(self) -> QWidget:
        """
        Return the Qt widget for this tool's UI.

        Returns:
            QWidget containing the tool's interface.
        """
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the tool's main functionality.

        Args:
            **kwargs: Tool-specific parameters.

        Returns:
            Dictionary containing execution results.
        """
        ...


class BaseToolPlugin:
    """
    Base class providing common plugin functionality.

    Plugins can inherit from this for convenience methods,
    though implementing ToolPlugin protocol directly is also valid.
    """

    metadata: PluginMetadata

    def __init__(self) -> None:
        self._widget: QWidget | None = None

    def get_widget(self) -> QWidget:
        """Override in subclass to return the tool's widget."""
        raise NotImplementedError("Subclass must implement get_widget()")

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Override in subclass to implement tool logic."""
        raise NotImplementedError("Subclass must implement execute()")

    def log(self, message: str) -> None:
        """Log a message with plugin context."""
        from loguru import logger

        logger.info(f"[{self.metadata.name}] {message}")
