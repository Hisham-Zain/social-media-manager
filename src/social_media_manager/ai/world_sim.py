import logging
import re

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class GeminiWorldSim:
    """
    Simulates audience reactions using the Hybrid Brain.
    """

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain: HybridBrain = brain if brain else HybridBrain()

    def get_reward(
        self, content: str, day: str, hour: int, platform: str = "twitter"
    ) -> int:
        """
        Predicts engagement score (-10 to +10).

        Args:
            content: The post content to evaluate.
            day: Day of the week.
            hour: Hour of the day (0-23).
            platform: Social media platform.

        Returns:
            Engagement score between -10 and +10, or 0 on error.
        """
        prompt = f"""
        Act as a Simulator for the {platform} algorithm.
        Score this post from -10 to +10 based on viral potential:
        "{content}" posted on {day} at {hour}:00.

        Rules:
        - Posting at 3AM is bad (- points)
        - High controversy is risky but viral (+ points)

        Return ONLY the integer number.
        """

        try:
            response = self.brain.think(prompt)

            if not response or response.startswith("Error:"):
                logger.warning("⚠️ WorldSim: Brain returned error")
                return 0

            # Extract number from response
            match = re.search(r"-?\d+", response)
            if match:
                score = int(match.group())
                # Clamp to valid range
                return max(-10, min(10, score))
            else:
                logger.warning(
                    f"⚠️ WorldSim: Could not parse score from: {response[:50]}"
                )
                return 0

        except ValueError as e:
            logger.error(f"❌ WorldSim: Score parsing failed: {e}")
            return 0
        except Exception as e:
            logger.error(f"❌ WorldSim: Unexpected error: {e}")
            return 0
