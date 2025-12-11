import json
import logging
from typing import Any

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class CampaignArchitect:
    """
    Plans multi-video content funnels.
    """

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()

    def generate_campaign(self, goal: str, niche: str) -> dict[str, Any] | None:
        logger.info(f"🏗️ Architecting campaign for {niche}...")
        try:
            prompt = f"Plan 5-video funnel for {goal} in {niche}. JSON Output: {{ 'campaign_name': '...', 'videos': [ {{'day': 1, 'type': '...', 'script_outline': '...'}} ] }}"
            res = self.brain.think(prompt, json_mode=True)
            return json.loads(res)
        except json.JSONDecodeError:
            logger.error("❌ Campaign Architect received invalid JSON.")
            return None
        except Exception as e:
            logger.error(f"❌ Campaign Architect Error: {e}")
            return None
