"""
Plugin Loader - Dynamic Plugin Discovery and Loading.

Scans the plugins directory and loads valid ToolPlugin implementations.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from . import PluginMetadata, ToolPlugin

if TYPE_CHECKING:
    pass


class PluginLoader:
    """
    Discovers and loads tool plugins dynamically.

    Scans the plugins directory for Python modules that
    contain classes implementing the ToolPlugin protocol.

    Usage:
        loader = PluginLoader()
        plugins = loader.discover()

        for plugin in plugins:
            print(f"Found: {plugin.metadata.name}")

        writing_tools = loader.get_by_category("writing")
    """

    def __init__(self, plugins_dir: Path | None = None) -> None:
        """
        Initialize the plugin loader.

        Args:
            plugins_dir: Directory to scan for plugins.
                        Defaults to the 'plugins' package directory.
        """
        self.plugins_dir = plugins_dir or Path(__file__).parent
        self._plugins: dict[str, ToolPlugin] = {}
        self._discovered = False

    def discover(self) -> list[ToolPlugin]:
        """
        Scan plugins directory and load all valid plugins.

        Returns:
            List of loaded ToolPlugin instances.
        """
        if self._discovered:
            return list(self._plugins.values())

        logger.debug(f"Discovering plugins in {self.plugins_dir}")

        # Scan for Python modules in plugins directory
        for importer, name, ispkg in pkgutil.iter_modules([str(self.plugins_dir)]):
            # Skip private modules
            if name.startswith("_"):
                continue

            try:
                # Import the module
                module = importlib.import_module(
                    f".{name}",
                    package="social_media_manager.plugins",
                )

                # Find plugin classes in the module
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue

                    attr = getattr(module, attr_name)

                    # Check if it's a class with PluginMetadata
                    if (
                        isinstance(attr, type)
                        and hasattr(attr, "metadata")
                        and isinstance(getattr(attr, "metadata", None), PluginMetadata)
                    ):
                        try:
                            plugin_instance = attr()
                            self._plugins[plugin_instance.metadata.name] = (
                                plugin_instance
                            )
                            logger.info(
                                f"Loaded plugin: {plugin_instance.metadata.name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to instantiate plugin {attr_name}: {e}"
                            )

            except ImportError as e:
                logger.warning(f"Failed to import plugin module {name}: {e}")
            except Exception as e:
                logger.error(f"Error loading plugin {name}: {e}")

        self._discovered = True
        return list(self._plugins.values())

    def get_by_category(self, category: str) -> list[ToolPlugin]:
        """
        Get plugins filtered by category.

        Args:
            category: Category to filter by (e.g., "writing", "audio").

        Returns:
            List of plugins in the specified category.
        """
        if not self._discovered:
            self.discover()

        return [p for p in self._plugins.values() if p.metadata.category == category]

    def get_by_name(self, name: str) -> ToolPlugin | None:
        """
        Get a plugin by its name.

        Args:
            name: The plugin's registered name.

        Returns:
            The plugin if found, None otherwise.
        """
        if not self._discovered:
            self.discover()

        return self._plugins.get(name)

    def get_all(self) -> list[ToolPlugin]:
        """
        Get all loaded plugins.

        Returns:
            List of all loaded plugins.
        """
        if not self._discovered:
            self.discover()

        return list(self._plugins.values())

    def get_categories(self) -> list[str]:
        """
        Get list of unique plugin categories.

        Returns:
            List of category names.
        """
        if not self._discovered:
            self.discover()

        return list(set(p.metadata.category for p in self._plugins.values()))


# Global plugin loader instance
_loader: PluginLoader | None = None


def get_plugin_loader() -> PluginLoader:
    """Get or create the global plugin loader."""
    global _loader
    if _loader is None:
        _loader = PluginLoader()
    return _loader
