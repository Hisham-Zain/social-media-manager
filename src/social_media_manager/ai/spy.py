import json
import logging
from typing import Any

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class CompetitorSpy:
    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()

    def analyze_competitor(
        self, name: str, platform: str = "YouTube"
    ) -> dict[str, Any] | None:
        logger.info(f"🕵️ Spying on {name}...")

        prompt = f"Analyze competitor '{name}' on {platform}. JSON: {{ 'strategy_breakdown': {{...}}, 'steal_this_strategy': '...' }}"

        try:
            res = self.brain.think(prompt, json_mode=True)
            return json.loads(res)
        except json.JSONDecodeError as e:
            logger.error(
                f"❌ Spy Agent failed to parse JSON for {name}. Raw response: {res[:100]}... Error: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"❌ Spy Agent unexpected error for {name}: {e}")
            return None
