"""
API Client for GUI-to-Backend Communication.

Provides a clean interface for the PyQt6 GUI to communicate with
the FastAPI backend server, enabling full GUI-backend decoupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from loguru import logger

from .config import config


@dataclass
class APIResponse:
    """Standardized API response wrapper."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class AgencyClient:
    """
    HTTP client for communicating with the AgencyOS backend API.

    The GUI uses this client to offload heavy operations to the
    background server process, keeping the UI responsive.

    Usage:
        client = AgencyClient()

        # Submit a job
        response = client.submit_job("video_render", {"script": "..."})

        # Check brain status
        status = client.brain_status()

        # Remote LLM inference
        result = client.brain_think("Generate a script about AI")
    """

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        """
        Initialize the API client.

        Args:
            base_url: Backend API URL. Defaults to config.BRAIN_API_URL.
            timeout: Request timeout in seconds. Defaults to config.BRAIN_API_TIMEOUT.
        """
        self.base_url = (base_url or config.BRAIN_API_URL).rstrip("/")
        self.timeout = timeout or config.BRAIN_API_TIMEOUT
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # =========================================================================
    # HEALTH & STATUS
    # =========================================================================

    def health(self) -> APIResponse:
        """Check if the backend server is healthy."""
        return self._get("/health")

    def status(self) -> APIResponse:
        """Get API status and version."""
        return self._get("/")

    # =========================================================================
    # BRAIN (LLM INFERENCE)
    # =========================================================================

    def brain_think(
        self,
        prompt: str,
        context: str = "",
        json_mode: bool = False,
    ) -> APIResponse:
        """
        Remote LLM inference via Brain Box.

        Args:
            prompt: The prompt to send to the LLM.
            context: Optional context to include.
            json_mode: If True, request JSON-formatted response.

        Returns:
            APIResponse with the LLM's response.
        """
        return self._post(
            "/api/v1/brain/think",
            {"prompt": prompt, "context": context, "json_mode": json_mode},
        )

    def brain_status(self) -> APIResponse:
        """Get brain availability and configuration."""
        return self._get("/api/v1/brain/status")

    # =========================================================================
    # JOB QUEUE
    # =========================================================================

    def submit_job(
        self,
        job_type: str,
        payload: dict[str, Any],
        priority: int = 5,
    ) -> APIResponse:
        """
        Submit a job to the background queue.

        Args:
            job_type: Type of job (e.g., "video_render", "music_compose").
            payload: Job parameters.
            priority: Job priority (1=low, 5=normal, 10=high, 20=urgent).

        Returns:
            APIResponse with job_id.
        """
        return self._post(
            "/jobs/submit",
            {"job_type": job_type, "payload": payload, "priority": priority},
        )

    def get_job(self, job_id: str) -> APIResponse:
        """Get job status by ID."""
        return self._get(f"/jobs/{job_id}")

    def list_jobs(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> APIResponse:
        """
        List jobs with optional status filter.

        Args:
            status: Filter by status (pending, running, completed, failed).
            limit: Maximum number of jobs to return.
        """
        params: dict[str, str | int] = {"limit": limit}
        if status:
            params["status"] = status
        return self._get("/jobs", params=params)

    def cancel_job(self, job_id: str) -> APIResponse:
        """Cancel a pending/queued job."""
        return self._delete(f"/jobs/{job_id}")

    # =========================================================================
    # CONTENT GENERATION
    # =========================================================================

    def generate_storyboard(
        self,
        script: str,
        project_name: str = "Untitled",
        target_duration: int = 60,
    ) -> APIResponse:
        """Generate a visual storyboard from a script."""
        return self._post(
            "/api/v1/storyboard/generate",
            {
                "script": script,
                "project_name": project_name,
                "target_duration": target_duration,
            },
        )

    def search_assets(
        self,
        query: str,
        asset_type: str | None = None,
        limit: int = 20,
    ) -> APIResponse:
        """Search assets semantically using CLIP embeddings."""
        return self._post(
            "/api/v1/assets/search",
            {"query": query, "asset_type": asset_type, "limit": limit},
        )

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    def update_config(self, updates: dict[str, Any]) -> APIResponse:
        """Update runtime configuration."""
        return self._post("/config/update", updates)

    # =========================================================================
    # INTERNAL HTTP METHODS
    # =========================================================================

    def _get(
        self,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> APIResponse:
        """Perform GET request."""
        try:
            resp = self._session.get(
                f"{self.base_url}{path}",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return APIResponse(success=True, data=resp.json())
        except requests.exceptions.ConnectionError:
            logger.warning(f"Backend not reachable at {self.base_url}")
            return APIResponse(success=False, error="Backend server not reachable")
        except requests.exceptions.Timeout:
            return APIResponse(success=False, error="Request timed out")
        except requests.exceptions.HTTPError as e:
            return APIResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return APIResponse(success=False, error=str(e))

    def _post(self, path: str, data: dict[str, Any]) -> APIResponse:
        """Perform POST request."""
        try:
            resp = self._session.post(
                f"{self.base_url}{path}",
                json=data,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return APIResponse(success=True, data=resp.json())
        except requests.exceptions.ConnectionError:
            logger.warning(f"Backend not reachable at {self.base_url}")
            return APIResponse(success=False, error="Backend server not reachable")
        except requests.exceptions.Timeout:
            return APIResponse(success=False, error="Request timed out")
        except requests.exceptions.HTTPError as e:
            return APIResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return APIResponse(success=False, error=str(e))

    def _delete(self, path: str) -> APIResponse:
        """Perform DELETE request."""
        try:
            resp = self._session.delete(
                f"{self.base_url}{path}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return APIResponse(success=True, data=resp.json())
        except requests.exceptions.ConnectionError:
            return APIResponse(success=False, error="Backend server not reachable")
        except requests.exceptions.Timeout:
            return APIResponse(success=False, error="Request timed out")
        except requests.exceptions.HTTPError as e:
            return APIResponse(success=False, error=str(e))
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return APIResponse(success=False, error=str(e))


# Singleton client instance
_client: AgencyClient | None = None


def get_client() -> AgencyClient:
    """Get or create the global API client."""
    global _client
    if _client is None:
        _client = AgencyClient()
    return _client
