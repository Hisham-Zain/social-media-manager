import logging

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class SalesAuditor:
    """Agent that generates sales audit reports for potential clients."""

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()

    def generate_audit(
        self, business_name: str, link: str, niche: str
    ) -> str | None:
        """
        Generate a growth audit email for a target business.

        Args:
            business_name: Name of the target business.
            link: Social media link to analyze.
            niche: Business niche/industry.

        Returns:
            Audit report text, or None if generation failed.
        """
        logger.info(f"📋 Auditor: Analyzing {business_name}...")

        try:
            prompt = (
                f"Act as sales consultant. Target: '{business_name}' ({niche}). "
                f"Link: {link}. Write a 'Growth Audit' email."
            )
            result = self.brain.think(prompt)

            if not result or result.startswith("Error:"):
                logger.error(f"❌ Auditor: Brain returned error for {business_name}")
                return None

            return result

        except Exception as e:
            logger.error(f"❌ Auditor Error for {business_name}: {e}")
            return None
