"""
REST API for AgencyOS.

Provides external API access via FastAPI.
Run with: uvicorn social_media_manager.api:app --reload
"""

import traceback
from datetime import datetime
from typing import Any

from loguru import logger

# Lazy import FastAPI to avoid mandatory dependency
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore
    BaseModel = object  # type: ignore


# Request/Response models
class ContentRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to generate content."""

    topic: str
    platform: str = "instagram"
    style: str | None = None
    duration: int = 60


class ContentResponse(BaseModel if FASTAPI_AVAILABLE else object):
    """Response with generated content."""

    success: bool
    content_id: str | None = None
    script: str | None = None
    caption: str | None = None
    error: str | None = None


class WebhookRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Incoming webhook request."""

    event: str
    data: dict[str, Any] = {}
    timestamp: str | None = None


class ScheduleRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to schedule content."""

    name: str
    task_type: str
    scheduled_time: str
    payload: dict[str, Any] = {}
    recurrence: str | None = None


class StatusResponse(BaseModel if FASTAPI_AVAILABLE else object):
    """API status response."""

    status: str
    version: str
    timestamp: str


# --- Brain Box (Remote Inference) Models ---


class ThinkRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request for brain inference."""

    prompt: str
    context: str = ""
    json_mode: bool = False


class ThinkResponse(BaseModel if FASTAPI_AVAILABLE else object):
    """Response from brain inference."""

    success: bool
    response: str | None = None
    error: str | None = None
    provider: str | None = None
    model: str | None = None


class BrainStatusResponse(BaseModel if FASTAPI_AVAILABLE else object):
    """Brain status response."""

    available: bool
    provider: str
    model: str
    fallback_provider: str
    fallback_model: str
    gpu_available: bool = False
    vram_free_mb: float | None = None


# --- Storyboard Models ---


class StoryboardRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to generate a storyboard."""

    script: str
    project_name: str = "Untitled"
    target_duration: int = 60
    generate_previews: bool = False  # Async preview generation


class SceneRegenerateRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to regenerate a scene."""

    storyboard_id: str
    scene_id: int


# --- Competitor Cloning Models ---


class CloneRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to analyze and clone a viral video."""

    url: str
    template_name: str | None = None
    create_template: bool = True


# --- Asset Management Models ---


class AssetSearchRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to search assets semantically."""

    query: str
    asset_type: str | None = None  # image, video, audio, document
    tags: list[str] | None = None
    limit: int = 20


class SceneSwapRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to swap a scene with stock footage."""

    storyboard_id: str
    scene_id: int
    search_query: str


def create_app() -> Any:
    """Create and configure the FastAPI app."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not installed. Run: pip install fastapi uvicorn")

    app = FastAPI(
        title="AgencyOS API",
        description="External API for AgencyOS content automation",
        version="2.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS for web clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Health endpoints
    # -------------------------------------------------------------------------

    @app.get("/", response_model=StatusResponse)
    async def root() -> StatusResponse:
        """API health check."""
        return StatusResponse(
            status="ok",
            version="2.4.0",
            timestamp=datetime.now().isoformat(),
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    # -------------------------------------------------------------------------
    # Brain Box (Remote Inference) endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/v1/brain/think", response_model=ThinkResponse)
    async def brain_think(request: ThinkRequest) -> ThinkResponse:
        """Remote inference endpoint for HybridBrain.

        This is the core Brain Box endpoint that allows the GUI to
        offload heavy LLM inference to a separate server process.
        """
        try:
            from .ai.brain import HybridBrain

            brain = HybridBrain()
            response = brain.think(
                prompt=request.prompt,
                context=request.context,
                json_mode=request.json_mode,
            )

            return ThinkResponse(
                success=True,
                response=response,
                provider=brain.provider,
                model=brain.model,
            )

        except ImportError as e:
            logger.error(f"Brain dependency missing: {e}")
            return ThinkResponse(success=False, error=f"Missing dependency: {e}")
        except Exception as e:
            logger.error(f"Brain inference error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return ThinkResponse(success=False, error=str(e))

    @app.get("/api/v1/brain/status", response_model=BrainStatusResponse)
    async def brain_status() -> BrainStatusResponse:
        """Check brain availability and configuration."""
        try:
            from .ai.brain import HybridBrain
            from .config import config

            brain = HybridBrain()

            # Check GPU
            gpu_available = False
            vram_free = None
            try:
                from .core.system_monitor import get_monitor

                monitor = get_monitor()
                status = monitor.get_status()
                if hasattr(status, "gpu") and status.gpu:
                    gpu_available = True
                    vram_free = (
                        status.gpu.vram_free_mb
                        if hasattr(status.gpu, "vram_free_mb")
                        else None
                    )
            except Exception:
                pass

            return BrainStatusResponse(
                available=True,
                provider=brain.provider,
                model=brain.model,
                fallback_provider=config.LLM_FALLBACK_PROVIDER,
                fallback_model=config.LLM_FALLBACK_MODEL,
                gpu_available=gpu_available,
                vram_free_mb=vram_free,
            )

        except ImportError as e:
            logger.error(f"Brain not available: {e}")
            return BrainStatusResponse(
                available=False,
                provider="none",
                model="none",
                fallback_provider="none",
                fallback_model="none",
            )
        except Exception as e:
            logger.error(f"Brain status error: {e}")
            return BrainStatusResponse(
                available=False,
                provider="error",
                model=str(e),
                fallback_provider="none",
                fallback_model="none",
            )

    # -------------------------------------------------------------------------
    # Job Queue endpoints
    # -------------------------------------------------------------------------

    class JobSubmitRequest(BaseModel if FASTAPI_AVAILABLE else object):
        """Request to submit a job."""

        job_type: str
        payload: dict[str, Any] = {}
        priority: int = 5  # 1=low, 5=normal, 10=high, 20=urgent

    @app.post("/jobs/submit")
    async def submit_job(request: JobSubmitRequest) -> dict[str, Any]:
        """Submit a job to the background queue."""
        try:
            from .job_queue import JobPriority, get_queue

            queue = get_queue()

            # Map integer priority to enum
            priority_map = {
                1: JobPriority.LOW,
                5: JobPriority.NORMAL,
                10: JobPriority.HIGH,
                20: JobPriority.URGENT,
            }
            priority = priority_map.get(request.priority, JobPriority.NORMAL)

            job_id = queue.submit(request.job_type, request.payload, priority)

            return {
                "success": True,
                "job_id": job_id,
                "job_type": request.job_type,
            }

        except Exception as e:
            logger.error(f"Job submit error: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str) -> dict[str, Any]:
        """Get job status by ID."""
        try:
            from .job_queue import get_queue

            queue = get_queue()
            job = queue.get_job(job_id)

            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            return {
                "success": True,
                "job": {
                    "id": job.id,
                    "job_type": job.job_type,
                    "status": job.status.value,
                    "progress": job.progress,
                    "result": job.result,
                    "error": job.error,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get job error: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/jobs")
    async def list_jobs(
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List jobs with optional status filter."""
        try:
            from .job_queue import JobStatus, get_queue

            queue = get_queue()

            # Convert string status to enum if provided
            status_enum = None
            if status:
                try:
                    status_enum = JobStatus(status)
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid status: {status}"
                    )

            jobs = queue.get_jobs(status=status_enum, limit=limit)

            return {
                "success": True,
                "count": len(jobs),
                "jobs": [
                    {
                        "id": j.id,
                        "job_type": j.job_type,
                        "status": j.status.value,
                        "progress": j.progress,
                        "created_at": j.created_at,
                    }
                    for j in jobs
                ],
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"List jobs error: {e}")
            return {"success": False, "error": str(e)}

    @app.delete("/jobs/{job_id}")
    async def cancel_job(job_id: str) -> dict[str, Any]:
        """Cancel a pending/queued job."""
        try:
            from .job_queue import get_queue

            queue = get_queue()
            success = queue.cancel_job(job_id)

            if not success:
                raise HTTPException(
                    status_code=400,
                    detail="Job cannot be cancelled (not pending/queued)",
                )

            return {"success": True, "job_id": job_id}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cancel job error: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Storyboard endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/v1/storyboard/generate")
    async def generate_storyboard(request: StoryboardRequest) -> dict[str, Any]:
        """Generate a visual storyboard from a script."""
        try:
            from .ai.director import VideoDirector

            director = VideoDirector()
            storyboard = director.generate_storyboard(
                script=request.script,
                project_name=request.project_name,
                target_duration=request.target_duration,
                generate_previews=request.generate_previews,
            )

            return {
                "success": True,
                "storyboard": storyboard.model_dump(),
            }

        except ImportError as e:
            logger.error(f"Storyboard dependency missing: {e}")
            return {"success": False, "error": f"Missing dependency: {e}"}
        except Exception as e:
            logger.error(f"Storyboard generation error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Asset Management endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/v1/assets/search")
    async def asset_search(request: AssetSearchRequest) -> dict[str, Any]:
        """Search assets semantically using CLIP embeddings."""
        try:
            from .core.asset_vault import get_asset_vault

            vault = get_asset_vault()
            results = vault.search(
                query=request.query,
                asset_type=request.asset_type,
                tags=request.tags,
                limit=request.limit,
            )

            return {
                "success": True,
                "count": len(results),
                "assets": results,
            }

        except ImportError as e:
            logger.error(f"Asset vault dependency missing: {e}")
            return {"success": False, "error": f"Missing dependency: {e}"}
        except Exception as e:
            logger.error(f"Asset search error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return {"success": False, "error": str(e)}

    @app.get("/api/v1/assets/stats")
    async def asset_stats() -> dict[str, Any]:
        """Get asset vault statistics."""
        try:
            from .core.asset_vault import get_asset_vault

            vault = get_asset_vault()
            stats = vault.get_stats()
            return {"success": True, "stats": stats}

        except Exception as e:
            logger.error(f"Asset stats error: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Scene Management endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/v1/storyboard/regenerate")
    async def regenerate_scene(request: SceneRegenerateRequest) -> dict[str, Any]:
        """Regenerate a specific scene in a storyboard."""
        try:
            from .ai.director import VideoDirector

            director = VideoDirector()
            # Note: Implementation depends on storyboard storage
            # For now, return placeholder
            return {
                "success": True,
                "message": f"Scene {request.scene_id} regeneration started",
                "scene_id": request.scene_id,
            }

        except Exception as e:
            logger.error(f"Scene regeneration error: {e}")
            return {"success": False, "error": str(e)}

    @app.post("/api/v1/storyboard/swap-stock")
    async def swap_scene_stock(request: SceneSwapRequest) -> dict[str, Any]:
        """Swap a scene with stock footage based on search query."""
        try:
            from .ai.director import VideoDirector
            from .ai.stock_hunter import StockHunter

            hunter = StockHunter()
            results = hunter.search_images(request.search_query, count=5)

            return {
                "success": True,
                "scene_id": request.scene_id,
                "stock_options": results,
                "message": f"Found {len(results)} stock options for scene {request.scene_id}",
            }

        except ImportError as e:
            logger.error(f"Stock hunter dependency missing: {e}")
            return {"success": False, "error": f"Missing dependency: {e}"}
        except Exception as e:
            logger.error(f"Scene swap error: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Competitor Cloning endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/v1/clone/analyze")
    async def clone_analyze(request: CloneRequest) -> dict[str, Any]:
        """Analyze a viral video and optionally create a template.

        Downloads video, transcribes audio, analyzes structure, and
        extracts reusable patterns for content reproduction.
        """
        try:
            from .ai.viral_cloner import ViralCloner

            cloner = ViralCloner()

            # Analyze video
            analysis = cloner.analyze_video(request.url)
            if not analysis:
                return {
                    "success": False,
                    "error": "Failed to analyze video. Check URL and try again.",
                }

            result: dict[str, Any] = {
                "success": True,
                "analysis": analysis.to_dict(),
            }

            # Optionally create template
            if request.create_template:
                template_id = cloner.clone_to_template_manager(
                    url=request.url,
                    template_name=request.template_name,
                )
                result["template_id"] = template_id

            return result

        except ImportError as e:
            logger.error(f"Clone dependency missing: {e}")
            return {"success": False, "error": f"Missing dependency: {e}"}
        except Exception as e:
            logger.error(f"Clone analysis error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Content endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/content/generate", response_model=ContentResponse)
    async def generate_content(request: ContentRequest) -> ContentResponse:
        """Generate content using AI."""
        try:
            from .ai import HybridBrain

            brain = HybridBrain()

            # Generate script
            script = await brain.generate(
                f"Create a {request.platform} video script about: {request.topic}. "
                f"Target duration: {request.duration} seconds. "
                f"Style: {request.style or 'engaging and informative'}."
            )

            # Generate caption
            caption = await brain.generate(
                f"Create a {request.platform} caption for this script: {script[:500]}..."
            )

            import hashlib

            content_id = hashlib.md5(
                f"{request.topic}_{datetime.now()}".encode()
            ).hexdigest()[:12]

            logger.info(f"📝 Generated content: {content_id}")

            return ContentResponse(
                success=True,
                content_id=content_id,
                script=script,
                caption=caption,
            )

        except ImportError as e:
            logger.error(f"Content generation dependency missing: {e}")
            return ContentResponse(success=False, error=f"Missing dependency: {e}")
        except ValueError as e:
            logger.error(f"Content generation validation error: {e}")
            return ContentResponse(success=False, error=f"Invalid input: {e}")
        except Exception as e:
            logger.error(f"Content generation error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return ContentResponse(success=False, error=str(e))

    @app.get("/api/content/{content_id}")
    async def get_content(content_id: str) -> dict[str, Any]:
        """Get content by ID."""
        # TODO: Integrate with database
        raise HTTPException(status_code=404, detail="Content not found")

    # -------------------------------------------------------------------------
    # Webhook endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/webhooks/receive")
    async def receive_webhook(request: WebhookRequest) -> dict[str, Any]:
        """Receive incoming webhook."""
        try:
            from .core.webhooks import get_webhook_manager

            manager = get_webhook_manager()
            manager.trigger(f"external.{request.event}", request.data)

            logger.info(f"🔗 Received webhook: {request.event}")

            return {"success": True, "event": request.event}

        except ImportError as e:
            logger.error(f"Webhook dependency missing: {e}")
            raise HTTPException(status_code=500, detail=f"Missing dependency: {e}")
        except KeyError as e:
            logger.error(f"Webhook missing key: {e}")
            raise HTTPException(status_code=400, detail=f"Missing field: {e}")
        except Exception as e:
            logger.error(f"Webhook error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/webhooks")
    async def list_webhooks() -> list[dict[str, Any]]:
        """List registered webhooks."""
        from .core.webhooks import get_webhook_manager

        manager = get_webhook_manager()
        return [w.to_dict() for w in manager.list_webhooks()]

    # -------------------------------------------------------------------------
    # Scheduler endpoints
    # -------------------------------------------------------------------------

    @app.post("/api/schedule")
    async def schedule_task(request: ScheduleRequest) -> dict[str, Any]:
        """Schedule a new task."""
        try:
            from .core.scheduler import get_scheduler

            scheduler = get_scheduler()
            task = scheduler.schedule(
                name=request.name,
                task_type=request.task_type,
                scheduled_time=request.scheduled_time,
                payload=request.payload,
                recurrence=request.recurrence,
            )

            return {
                "success": True,
                "task_id": task.id,
                "scheduled_time": task.scheduled_time,
            }

        except ImportError as e:
            logger.error(f"Scheduler dependency missing: {e}")
            raise HTTPException(status_code=500, detail=f"Missing dependency: {e}")
        except ValueError as e:
            logger.error(f"Schedule validation error: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
        except Exception as e:
            logger.error(f"Schedule error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/schedule")
    async def list_tasks(status: str | None = None) -> list[dict[str, Any]]:
        """List scheduled tasks."""
        from .core.scheduler import get_scheduler

        scheduler = get_scheduler()
        tasks = scheduler.list_tasks(status=status)
        return [t.to_dict() for t in tasks]

    @app.delete("/api/schedule/{task_id}")
    async def cancel_task(task_id: str) -> dict[str, bool]:
        """Cancel a scheduled task."""
        from .core.scheduler import get_scheduler

        scheduler = get_scheduler()
        success = scheduler.cancel(task_id)

        if not success:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"success": True}

    # -------------------------------------------------------------------------
    # Analytics endpoints
    # -------------------------------------------------------------------------

    @app.get("/api/analytics/ai")
    async def get_ai_analytics(days: int = 30) -> dict[str, Any]:
        """Get AI usage analytics."""
        from .core.usage_tracker import get_ai_tracker

        tracker = get_ai_tracker()
        return tracker.get_costs(days=days)

    @app.get("/api/analytics/content")
    async def get_content_analytics(days: int = 30) -> dict[str, Any]:
        """Get content performance analytics."""
        from .core.usage_tracker import get_content_tracker

        tracker = get_content_tracker()
        return tracker.get_summary(days=days)

    # -------------------------------------------------------------------------
    # System endpoints
    # -------------------------------------------------------------------------

    @app.get("/api/system/health")
    async def get_system_health() -> dict[str, Any]:
        """Get system health status."""
        try:
            from .core.system_monitor import get_monitor

            monitor = get_monitor()
            status = monitor.get_status()

            return {
                "gpu": {
                    "name": status.gpu.name if status.gpu else None,
                    "vram_free_mb": status.gpu.vram_free_mb if status.gpu else None,
                    "utilization": status.gpu.utilization if status.gpu else None,
                },
                "cpu_percent": status.cpu_percent,
                "ram_used_mb": status.ram_used_mb,
                "ram_total_mb": status.ram_total_mb,
            }

        except ImportError as e:
            logger.warning(f"System monitor not available: {e}")
            return {"error": f"Monitor unavailable: {e}"}
        except Exception as e:
            logger.error(f"System health error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return {"error": str(e)}

    logger.info("🚀 AgencyOS API created")
    return app


# Create app instance for uvicorn
app = create_app() if FASTAPI_AVAILABLE else None


def run_api(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server."""
    if not FASTAPI_AVAILABLE:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
        return

    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api()
