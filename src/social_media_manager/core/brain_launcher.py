"""
Brain Box Launcher for AgencyOS.

Manages the lifecycle of the remote Brain API server.
Allows the GUI to spawn/stop the heavy AI inference in a separate process.
"""

import atexit
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests
from loguru import logger


class BrainLauncher:
    """
    Launch and manage the Brain API server subprocess.

    The Brain Box architecture decouples heavy AI inference from the GUI,
    preventing UI freezes and allowing the brain to run on separate hardware.

    Example:
        launcher = BrainLauncher()
        if launcher.start():
            # Brain is ready, GUI can now use remote mode
            ...
        launcher.stop()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Initialize the launcher."""
        self.host = host
        self.port = port
        self.process: subprocess.Popen[bytes] | None = None
        self._api_url = f"http://localhost:{port}"
        self._max_retries = 3
        self._retry_delay = 2
        self._auto_restart = True
        self._monitor_thread: threading.Thread | None = None
        self._stop_monitor = False
        self._consecutive_failures = 0

        # Register cleanup on exit
        atexit.register(self.stop)

    @property
    def api_url(self) -> str:
        """Get the API base URL."""
        return self._api_url

    def start(self, timeout: int = 30) -> bool:
        """
        Start the API server in a subprocess.

        Args:
            timeout: Maximum time to wait for server to become healthy.

        Returns:
            True if server started successfully, False otherwise.
        """
        if self.is_healthy():
            logger.info("🧠 Brain Box already running")
            return True

        if self.process and self.process.poll() is None:
            logger.warning("⚠️ Brain Box process exists but not responding")
            self.stop()

        logger.info(f"🚀 Starting Brain Box on port {self.port}...")

        try:
            # Build the command to run the API server
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "social_media_manager.api:app",
                "--host",
                self.host,
                "--port",
                str(self.port),
            ]

            # Start the subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent.parent,  # Project root
            )

            # Wait for server to become healthy
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.is_healthy():
                    logger.info(f"✅ Brain Box started on {self._api_url}")
                    return True
                time.sleep(0.5)

            # Timeout - check if process died
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                logger.error(f"❌ Brain Box failed to start:\n{stderr.decode()}")
            else:
                logger.error(f"❌ Brain Box timeout after {timeout}s")

            return False

        except Exception as e:
            logger.error(f"❌ Failed to launch Brain Box: {e}")
            return False

    def stop(self) -> None:
        """Stop the API server if running."""
        if self.process:
            if self.process.poll() is None:
                logger.info("🛑 Stopping Brain Box...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("⚠️ Brain Box not responding, killing...")
                    self.process.kill()
            self.process = None

    def is_healthy(self) -> bool:
        """Check if the server is responding to health checks."""
        try:
            response = requests.get(f"{self._api_url}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_status(self) -> dict:
        """Get detailed status of the Brain Box."""
        if not self.is_healthy():
            return {
                "running": False,
                "url": self._api_url,
                "pid": self.process.pid if self.process else None,
            }

        try:
            response = requests.get(f"{self._api_url}/api/v1/brain/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "running": True,
                    "url": self._api_url,
                    "pid": self.process.pid if self.process else None,
                    **data,
                }
        except Exception:
            pass

        return {
            "running": True,
            "url": self._api_url,
            "pid": self.process.pid if self.process else None,
        }

    def restart(self) -> bool:
        """Restart the Brain Box server."""
        self.stop()
        time.sleep(1)
        return self.start()

    def start_monitor(self, check_interval: int = 10) -> None:
        """Start background monitor for auto-restart on failure."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return  # Already monitoring

        self._stop_monitor = False

        def monitor_loop() -> None:
            while not self._stop_monitor:
                time.sleep(check_interval)
                if self._stop_monitor:
                    break

                if not self.is_healthy():
                    self._consecutive_failures += 1
                    logger.warning(
                        f"⚠️ Brain Box unhealthy (failure {self._consecutive_failures}/{self._max_retries})"
                    )

                    if (
                        self._auto_restart
                        and self._consecutive_failures <= self._max_retries
                    ):
                        logger.info("🔄 Attempting Brain Box restart...")
                        time.sleep(self._retry_delay)
                        if self.restart():
                            self._consecutive_failures = 0
                            logger.info("✅ Brain Box recovered")
                        else:
                            logger.error("❌ Brain Box restart failed")
                else:
                    self._consecutive_failures = 0

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("👁️ Brain Box monitor started")

    def stop_monitor(self) -> None:
        """Stop the background monitor."""
        self._stop_monitor = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None
            logger.info("👁️ Brain Box monitor stopped")


# Singleton instance
_launcher: BrainLauncher | None = None


def get_brain_launcher(port: int = 8000) -> BrainLauncher:
    """Get or create the Brain Box launcher singleton."""
    global _launcher
    if _launcher is None:
        _launcher = BrainLauncher(port=port)
    return _launcher
