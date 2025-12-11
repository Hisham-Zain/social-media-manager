import json
import logging
from typing import Any

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class ContentRepurposer:
    """
    Turns one video into a Multi-Channel Campaign using AI.
    """

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()

    def transmute(self, video_title: str, transcript: str) -> dict[str, Any] | None:
        """
        Repurposes video content into social media assets.
        """
        logger.info(f"⚗️ Transmuting content: {video_title}...")

        prompt = f"""
        SOURCE TRANSCRIPT:
        "{transcript[:15000]}"... [truncated]

        TASK:
        Repurpose this video into social assets.

        Output JSON with keys:
        1. 'linkedin_post': Professional, value-driven (200 words).
        2. 'twitter_thread': Array of 5 tweet strings.
        3. 'newsletter': A summary for email.
        """

        try:
            response = self.brain.think(prompt, json_mode=True)
            return json.loads(response)
        except Exception as e:
            logger.error(f"❌ Repurposing failed: {e}")
            return None
