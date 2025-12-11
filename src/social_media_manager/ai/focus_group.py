import json
import logging
from typing import Any

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class DigitalFocusGroup:
    """
    A synthetic audience that reviews content before it goes live.
    """

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()

    def evaluate(
        self, content_draft: str, media_description: str = ""
    ) -> dict[str, Any]:
        logger.info("⚖️ Convening Digital Focus Group...")

        prompt = f"""
        Act as a Digital Focus Group with 4 personas:
        1. The Skeptic (Cynical)
        2. The Hype Beast (Excitable)
        3. The Expert (Fact-checker)
        4. The Brand Safe (Cautious)

        TASK: Critique this post.
        [POST]: "{content_draft}"
        [VISUAL]: "{media_description}"

        OUTPUT JSON:
        {{
            "reviews": {{
                "skeptic": {{ "score": 1-10, "comment": "..." }},
                "hype_beast": {{ "score": 1-10, "comment": "..." }},
                "expert": {{ "score": 1-10, "comment": "..." }},
                "safety": {{ "score": 1-10, "comment": "..." }}
            }},
            "final_score": (average 1-100),
            "verdict": "PUBLISH" or "REVISE",
            "primary_complaint": "..."
        }}
        """

        default_response = {
            "score": 0,
            "verdict": "ERROR",
            "primary_complaint": "AI Analysis Failed",
            "reviews": {},
        }

        try:
            res = self.brain.think(prompt, json_mode=True)
            return json.loads(res)
        except json.JSONDecodeError:
            logger.error("❌ Focus Group: AI returned invalid JSON.")
            return default_response
        except Exception as e:
            logger.error(f"❌ Focus Group Error: {e}")
            return default_response
