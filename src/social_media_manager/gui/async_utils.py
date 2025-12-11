"""
Async utilities for Qt-asyncio bridge.

Provides helpers for running async code from PyQt6 GUI components
without blocking the UI thread.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, TypeVar

from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

T = TypeVar("T")


class AsyncRunner(QObject):
    """
    Bridge between async coroutines and Qt signals.

    Allows GUI components to run async operations and receive results
    via Qt signals, maintaining thread safety.

    Usage:
        runner = AsyncRunner()
        runner.finished.connect(self._on_result)
        runner.error.connect(self._on_error)
        runner.run(some_async_function())
    """

    # Emitted when async operation completes successfully
    finished = pyqtSignal(object)
    # Emitted when async operation raises an exception
    error = pyqtSignal(Exception)
    # Emitted for progress updates (0.0 - 1.0)
    progress = pyqtSignal(float, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._task: asyncio.Task | None = None

    def run(self, coro: Coroutine[Any, Any, T]) -> None:
        """
        Schedule a coroutine to run on the qasync event loop.

        Args:
            coro: The coroutine to execute.
        """

        async def wrapper() -> None:
            try:
                result = await coro
                self.finished.emit(result)
            except asyncio.CancelledError:
                logger.debug("Async task was cancelled")
            except Exception as e:
                logger.error(f"Async task error: {e}")
                self.error.emit(e)

        try:
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(wrapper())
        except RuntimeError:
            logger.error("No event loop available - is qasync initialized?")
            self.error.emit(RuntimeError("No async event loop available"))

    def cancel(self) -> None:
        """Cancel the running async task if any."""
        if self._task and not self._task.done():
            self._task.cancel()

    @property
    def is_running(self) -> bool:
        """Check if a task is currently running."""
        return self._task is not None and not self._task.done()


def run_async(coro: Coroutine[Any, Any, T]) -> asyncio.Task:
    """
    Convenience function to schedule a coroutine.

    Args:
        coro: The coroutine to execute.

    Returns:
        The asyncio Task wrapping the coroutine.
    """
    loop = asyncio.get_event_loop()
    return loop.create_task(coro)


async def gather_with_progress(
    coros: list[Coroutine],
    progress_callback: Callable[[float], None] | None = None,
) -> list[Any]:
    """
    Run multiple coroutines with aggregate progress tracking.

    Args:
        coros: List of coroutines to execute.
        progress_callback: Called with progress (0.0 - 1.0) as tasks complete.

    Returns:
        List of results from all coroutines.
    """
    total = len(coros)
    completed = 0
    results: list[Any] = []

    async def track(coro: Coroutine) -> Any:
        nonlocal completed
        result = await coro
        completed += 1
        if progress_callback:
            progress_callback(completed / total)
        return result

    tasks = [track(c) for c in coros]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
