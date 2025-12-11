from typing import Any

from fastapi import FastAPI

from ..core.orchestrator import SocialMediaManager

app = FastAPI(title="AI Manager API")
manager = SocialMediaManager()


@app.post("/generate")
def generate(topic: str, media_type: str = "video") -> dict[str, Any]:
    """
    Endpoint to generate content.

    Args:
        topic (str): The topic for content generation.
        media_type (str, optional): The type of media to generate. Defaults to "video".

    Returns:
        dict: The generated content details.
    """
    return manager.create_from_scratch(topic, media_type)
