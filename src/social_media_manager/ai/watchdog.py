import logging

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class CompetitorWatchdog:
    """
    Monitors competitors and generates SWOT analysis.
    """

    def __init__(self, brain: HybridBrain | None = None):
        self.brain = brain if brain else HybridBrain()

    def analyze(self, competitor_name: str, observations: str) -> str:
        """
        Generates a text-based SWOT analysis.
        """
        logger.info(f"🐕 Watchdog: Analyzing {competitor_name}...")

        prompt = (
            f"Competitor: {competitor_name}\n"
            f"Notes: {observations}\n"
            "Task: Create a SWOT Analysis and a 3-step action plan to beat them."
        )

        try:
            return self.brain.think(prompt)
        except Exception as e:
            logger.error(f"❌ Watchdog Analysis Failed: {e}")
            return "Analysis failed due to AI error."
