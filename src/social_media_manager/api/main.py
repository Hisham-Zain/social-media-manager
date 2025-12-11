from typing import Any

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from social_media_manager.core.orchestrator import SocialMediaManager

app = FastAPI(title="AI Manager Pro API")
manager = SocialMediaManager()


class VideoRequest(BaseModel):
    """
    Request model for video processing.

    Attributes:
        path (str): Path to the video file.
        platform (str): Target platform (default: youtube).
    """

    path: str
    platform: str = "youtube"


class GenRequest(BaseModel):
    """
    Request model for content generation.

    Attributes:
        topic (str): The topic for content generation.
        type (str): The type of content to generate (default: video).
    """

    topic: str
    type: str = "video"


@app.post("/process")
async def process_video(
    req: VideoRequest, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """
    Endpoint to process a video in the background.

    Args:
        req (VideoRequest): The video processing request.
        background_tasks (BackgroundTasks): FastAPI background tasks handler.

    Returns:
        dict: Status message and file path.
    """
    # Run in background so API doesn't hang
    background_tasks.add_task(manager.process_video, req.path, [req.platform])
    return {"status": "Processing started", "file": req.path}


@app.post("/generate")
def generate_content(req: GenRequest) -> dict[str, Any]:
    """
    Endpoint to generate content from scratch.

    Args:
        req (GenRequest): The content generation request.

    Returns:
        dict: The generated content details.
    """
    return manager.create_from_scratch(req.topic, req.type)


@app.get("/stats")
def get_stats() -> list[dict[str, Any]]:
    """
    Endpoint to retrieve analytics statistics.

    Returns:
        list[dict]: A list of analytics records.
    """
    return manager.db.get_analytics().to_dict(orient="records")
