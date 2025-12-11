import logging

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class CriticAgent:
    """
    Agent that reviews and refines content drafts.
    """

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()

    def roast_and_refine(self, draft_caption: str) -> dict[str, str]:
        """
        Critiques a caption and provides a better version.
        """
        logger.info("🧐 Critic: Reviewing draft...")

        result = {
            "original": draft_caption,
            "critique": "Analysis failed.",
            "final_version": draft_caption,
        }

        try:
            critique = self.brain.think(
                f"Critique this caption for engagement: '{draft_caption}'"
            )
            final = self.brain.think(
                f"Rewrite this caption based on this feedback: '{critique}'. Return ONLY the new caption."
            )

            result["critique"] = critique
            result["final_version"] = final.strip('"')  # Remove accidental quotes
            return result

        except Exception as e:
            logger.error(f"❌ Critic Error: {e}")
            return result
