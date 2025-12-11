"""
Main window for the AgencyOS Desktop GUI.

Command Center architecture with dockable panels and keyboard shortcuts.
Includes backend server subprocess management for full GUI-backend decoupling.
"""

from __future__ import annotations

import atexit
import subprocess
import sys
import time
from typing import TYPE_CHECKING

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from .sidebar import Sidebar
from .styles import DARK_THEME
from .views.ai_tools import AIToolsView
from .views.alchemy import AlchemyView
from .views.asset_browser import AssetBrowser
from .views.automation import AutomationView
from .views.brand_voice import BrandVoiceView
from .views.community import CommunityView
from .views.content_studio import ContentStudioView
from .views.dashboard import DashboardView
from .views.job_queue import JobQueueView
from .views.media_library import MediaLibraryView
from .views.settings import SettingsView
from .views.storyboard import StoryboardView
from .views.strategy import StrategyRoomView
from .views.war_room import WarRoomView
from .widgets.toasts import show_toast

if TYPE_CHECKING:
    pass


class BackendServerManager:
    """
    Manages the FastAPI backend server as a subprocess.

    The GUI acts as a lightweight client that communicates with the
    backend via HTTP, enabling full decoupling of UI from heavy processing.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self._process: subprocess.Popen | None = None
        self._started = False

    def start(self) -> bool:
        """
        Start the backend server as a subprocess.

        Returns:
            True if server started successfully.
        """
        import urllib.error
        import urllib.request

        if self._process is not None:
            logger.warning("Backend server already running")
            return True

        try:
            # Start uvicorn as subprocess
            self._process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "social_media_manager.api:app",
                    "--host",
                    self.host,
                    "--port",
                    str(self.port),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Don't inherit stdin to avoid issues
                stdin=subprocess.DEVNULL,
            )

            # Wait for server to start with health check retries
            max_retries = 5
            for attempt in range(max_retries):
                time.sleep(0.5)

                # Check if process crashed
                if self._process.poll() is not None:
                    # Process exited - capture stderr
                    _, stderr = self._process.communicate()
                    error_msg = stderr.decode().strip() if stderr else "No error output"
                    logger.error(f"Backend server crashed: {error_msg[:500]}")
                    self._process = None
                    return False

                # Try health check
                try:
                    url = f"http://{self.host}:{self.port}/health"
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=1):
                        pass
                    # Server is responding!
                    self._started = True
                    logger.info(
                        f"🚀 Backend server started at http://{self.host}:{self.port}"
                    )
                    atexit.register(self.stop)
                    return True
                except (urllib.error.URLError, TimeoutError):
                    # Server not ready yet, continue waiting
                    if attempt < max_retries - 1:
                        logger.debug(
                            f"Waiting for backend server (attempt {attempt + 1}/{max_retries})"
                        )

            # Max retries reached - server might still be starting
            if self._process.poll() is None:
                self._started = True
                logger.info(
                    f"🚀 Backend server started at http://{self.host}:{self.port}"
                )
                atexit.register(self.stop)
                return True

            logger.error("Backend server failed to start within timeout")
            return False

        except FileNotFoundError:
            logger.error("uvicorn not found - install with: pip install uvicorn")
            return False
        except Exception as e:
            logger.error(f"Failed to start backend server: {e}")
            return False

    def stop(self) -> None:
        """Stop the backend server gracefully."""
        if self._process is None:
            return

        try:
            self._process.terminate()
            self._process.wait(timeout=5)
            logger.info("🛑 Backend server stopped")
        except subprocess.TimeoutExpired:
            self._process.kill()
            logger.warning("Backend server killed (timeout)")
        except Exception as e:
            logger.error(f"Error stopping backend server: {e}")
        finally:
            self._process = None
            self._started = False

    @property
    def is_running(self) -> bool:
        """Check if the backend server is running."""
        if self._process is None:
            return False
        return self._process.poll() is None


# Global server manager instance
_server_manager: BackendServerManager | None = None


def get_server_manager() -> BackendServerManager:
    """Get or create the global server manager."""
    global _server_manager
    if _server_manager is None:
        _server_manager = BackendServerManager()
    return _server_manager


class MainWindow(QMainWindow):
    """Main application window with dockable panels and keyboard shortcuts."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AgencyOS - AI Social Media Manager")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(DARK_THEME)

        # Enable dock nesting and animations
        self.setDockNestingEnabled(True)
        self.setAnimated(True)

        # Instance attributes
        self.sidebar: Sidebar
        self.stack: QStackedWidget
        self.views: list[QWidget]
        self.job_dock: QDockWidget
        self.library_dock: QDockWidget

        self._setup_ui()
        self._setup_docks()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        """Set up the main layout with sidebar and stacked views."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Sidebar Navigation
        self.sidebar = Sidebar()
        _ = self.sidebar.navigation_changed.connect(self._switch_view)
        layout.addWidget(self.sidebar)

        # 2. Stacked Views (main content area)
        self.stack = QStackedWidget()
        self.views = [
            DashboardView(),  # Index 0
            ContentStudioView(),  # Index 1
            StoryboardView(),  # Index 2
            AssetBrowser(),  # Index 3
            MediaLibraryView(),  # Index 4
            AutomationView(),  # Index 5
            StrategyRoomView(),  # Index 6
            AIToolsView(),  # Index 7
            JobQueueView(),  # Index 8
            CommunityView(),  # Index 9
            BrandVoiceView(),  # Index 10
            WarRoomView(),  # Index 11
            AlchemyView(),  # Index 12
            SettingsView(),  # Index 13
        ]

        for view in self.views:
            _ = self.stack.addWidget(view)

        # Connect Dashboard's navigation signal
        dashboard = self.views[0]
        _ = dashboard.navigate_to_view.connect(self._dashboard_navigate)

        layout.addWidget(self.stack, 1)

    def _setup_docks(self) -> None:
        """Create dockable tool panels."""
        # Job Queue - Bottom
        self.job_dock = self._add_dock(
            "📋 Job Queue",
            JobQueueView(),
            Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        self.job_dock.setMaximumHeight(250)

        # Media Library - Right (initially hidden)
        self.library_dock = self._add_dock(
            "📚 Media Library",
            MediaLibraryView(),
            Qt.DockWidgetArea.RightDockWidgetArea,
        )
        self.library_dock.hide()

    def _setup_shortcuts(self) -> None:
        """Set up global keyboard shortcuts."""
        shortcuts: list[tuple[str, callable]] = [
            ("Ctrl+1", lambda: self._switch_view(0)),  # Dashboard
            ("Ctrl+2", lambda: self._switch_view(1)),  # Content Studio
            ("Ctrl+3", lambda: self._switch_view(2)),  # Storyboard
            ("Ctrl+4", lambda: self._switch_view(3)),  # Asset Browser
            ("Ctrl+5", lambda: self._switch_view(4)),  # Media Library
            ("Ctrl+6", lambda: self._switch_view(5)),  # Automation
            ("Ctrl+7", lambda: self._switch_view(6)),  # Strategy
            ("Ctrl+8", lambda: self._switch_view(7)),  # AI Tools
            ("Ctrl+9", lambda: self._switch_view(8)),  # Job Queue
            ("Ctrl+0", lambda: self._switch_view(10)),  # Settings
            ("Ctrl+J", self.toggle_job_dock),  # Toggle Job Queue dock
            ("Ctrl+L", self.toggle_library_dock),  # Toggle Library dock
            ("Ctrl+Q", self.close),  # Quit
        ]

        for key, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            _ = shortcut.activated.connect(callback)

    def _add_dock(
        self,
        title: str,
        widget: QWidget,
        area: Qt.DockWidgetArea,
    ) -> QDockWidget:
        """Add a dockable panel."""
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        # Style the dock
        dock.setStyleSheet("""
            QDockWidget {
                font-size: 13px;
                font-weight: bold;
                color: #e2e8f0;
            }
            QDockWidget::title {
                background: #1e293b;
                padding: 8px 12px;
                border-bottom: 1px solid #334155;
            }
        """)

        self.addDockWidget(area, dock)
        return dock

    def _switch_view(self, index: int) -> None:
        """Switch the main content view and update sidebar."""
        self.stack.setCurrentIndex(index)
        self._update_sidebar_selection(index)

    def _dashboard_navigate(self, index: int) -> None:
        """Handle navigation from Dashboard Quick Actions."""
        self._switch_view(index)

    def _update_sidebar_selection(self, index: int) -> None:
        """Update sidebar visual selection."""
        try:
            # Reset previous button style
            prev_idx = getattr(self.sidebar, "_current_index", 0)
            if hasattr(self.sidebar, "_buttons") and prev_idx < len(
                self.sidebar._buttons
            ):
                self.sidebar._buttons[prev_idx].setStyleSheet(
                    self.sidebar._get_button_style(False)
                )
            # Set new button style
            if hasattr(self.sidebar, "_buttons") and index < len(self.sidebar._buttons):
                self.sidebar._buttons[index].setStyleSheet(
                    self.sidebar._get_button_style(True)
                )
                self.sidebar._current_index = index
        except Exception:
            pass  # Gracefully handle any sidebar state issues

    def show_toast(
        self,
        message: str,
        toast_type: str = "success",
        duration_ms: int = 3000,
    ) -> None:
        """Show a toast notification."""
        show_toast(self, message, toast_type, duration_ms)

    def toggle_library_dock(self) -> None:
        """Toggle the Media Library dock visibility."""
        self.library_dock.setVisible(not self.library_dock.isVisible())

    def toggle_job_dock(self) -> None:
        """Toggle the Job Queue dock visibility."""
        self.job_dock.setVisible(not self.job_dock.isVisible())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close - stop backend server."""
        server = get_server_manager()
        if server.is_running:
            server.stop()
        event.accept()


def main() -> None:
    """Launch the AgencyOS GUI with unified async event loop."""
    import asyncio
    import os
    import sys

    # Configure log level (default to INFO to suppress DEBUG spam)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=log_level)

    # Optionally start backend server (controlled by config)
    from ..config import config

    if config.USE_REMOTE_BRAIN:
        logger.info("Using remote brain - not starting local server")
    else:
        server = get_server_manager()
        if not server.start():
            logger.warning("Backend server not started - some features may be limited")

    try:
        from qasync import QEventLoop

        app = QApplication(sys.argv)

        # Create unified event loop that bridges PyQt6 and asyncio
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)

        window = MainWindow()
        window.show()

        # Run the unified event loop
        with loop:
            loop.run_forever()
    except ImportError:
        # Fallback if qasync not available
        logger.warning("qasync not installed, async operations may freeze GUI")
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
