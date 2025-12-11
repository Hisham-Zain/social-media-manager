"""
Trend Radar for AgencyOS.

Scans trending topics using pytrends (Google Trends API).
"""

import json
from typing import Any

from loguru import logger

from .brain import HybridBrain

# Try to import pytrends
try:
    from pytrends.request import TrendReq

    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    logger.warning("⚠️ pytrends not installed. Run: pip install pytrends")


class TrendRadar:
    """
    Scans Google Trends for niche topics using pytrends.

    Example:
        radar = TrendRadar()
        result = radar.check_trends("Tech")
        print(result)
        # {
        #     'trend': 'ChatGPT',
        #     'relevance_score': 9,
        #     'breaking_news_hook': 'OpenAI just released...',
        #     'reason': 'AI is hot in tech'
        # }
    """

    def __init__(self, brain: HybridBrain | None = None, geo: str = "US") -> None:
        self.brain = brain if brain else HybridBrain()
        self.geo = geo
        self._pytrends = None

        if PYTRENDS_AVAILABLE:
            try:
                self._pytrends = TrendReq(hl="en-US", tz=360)
            except Exception as e:
                logger.warning(f"⚠️ Failed to init pytrends: {e}")

    def check_trends(self, niche: str) -> dict[str, Any] | None:
        """
        Check trending topics relevant to a niche.

        Args:
            niche: Topic niche to filter trends (e.g., "Tech", "Gaming", "News")

        Returns:
            Dict with trend info or None if no trends found.
        """
        logger.info(f"📡 Radar scanning for niche: {niche}")

        try:
            trends = self._get_trending_searches()

            if not trends:
                logger.warning("No trends found")
                return None

            # Format trends for AI analysis
            trends_text = "\n".join([f"- {t}" for t in trends[:10]])

            prompt = (
                f"Current trending topics:\n{trends_text}\n\n"
                f"Niche: {niche}\n\n"
                "Select the ONE trend most relevant to this niche. "
                "Return JSON: { 'trend': '...', 'relevance_score': 1-10, "
                "'breaking_news_hook': 'catchy hook for content', 'reason': 'why relevant' }"
            )

            res = self.brain.think(prompt, json_mode=True)
            return json.loads(res)

        except Exception as e:
            logger.error(f"❌ Radar Error: {e}")
            return None

    def _get_trending_searches(self) -> list[str]:
        """Get trending searches from Google Trends."""
        if not PYTRENDS_AVAILABLE or not self._pytrends:
            return self._get_fallback_trends()

        try:
            # Get real-time trending searches
            trending = self._pytrends.trending_searches(pn=self.geo.lower())

            if trending is not None and not trending.empty:
                return trending[0].tolist()[:15]

            # Fallback to realtime trends
            return self._get_fallback_trends()

        except Exception as e:
            logger.warning(f"⚠️ pytrends error: {e}")
            return self._get_fallback_trends()

    def _get_fallback_trends(self) -> list[str]:
        """
        Fallback trends when API fails.
        Uses a mix of evergreen trending topics.
        """
        import random

        # Evergreen trending categories
        fallback_trends = [
            # Tech
            "AI tools",
            "ChatGPT",
            "New iPhone",
            "Tech layoffs",
            "Cryptocurrency",
            "Electric vehicles",
            "Smart home",
            # Entertainment
            "Netflix shows",
            "Gaming news",
            "Music releases",
            "Celebrity news",
            "Movie trailers",
            # General
            "Breaking news",
            "Sports highlights",
            "Weather alerts",
            "Stock market",
            "Health tips",
        ]

        random.shuffle(fallback_trends)
        return fallback_trends[:10]

    def get_related_queries(self, keyword: str) -> list[str]:
        """
        Get related queries for a keyword.

        Args:
            keyword: Topic to get related queries for.

        Returns:
            List of related search queries.
        """
        if not PYTRENDS_AVAILABLE or not self._pytrends:
            return []

        try:
            self._pytrends.build_payload([keyword], geo=self.geo, timeframe="now 7-d")
            related = self._pytrends.related_queries()

            if keyword in related and related[keyword]["rising"] is not None:
                return related[keyword]["rising"]["query"].tolist()[:10]

            return []

        except Exception as e:
            logger.warning(f"⚠️ Related queries error: {e}")
            return []

    def get_interest_over_time(self, keywords: list[str]) -> dict[str, Any]:
        """
        Get interest over time for keywords.

        Args:
            keywords: List of keywords to analyze.

        Returns:
            Dict with trend data.
        """
        if not PYTRENDS_AVAILABLE or not self._pytrends:
            return {}

        try:
            self._pytrends.build_payload(
                keywords[:5], geo=self.geo, timeframe="now 7-d"
            )
            interest = self._pytrends.interest_over_time()

            if interest is not None and not interest.empty:
                return {
                    col: interest[col].tolist()
                    for col in interest.columns
                    if col != "isPartial"
                }

            return {}

        except Exception as e:
            logger.warning(f"⚠️ Interest over time error: {e}")
            return {}
