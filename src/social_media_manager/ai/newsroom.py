import json
import logging

import feedparser

from .brain import HybridBrain

logger = logging.getLogger(__name__)


class Newsroom:
    """
    Agent that monitors RSS feeds for breaking news opportunities.
    """

    def __init__(
        self,
        rss_url: str = "http://feeds.feedburner.com/TechCrunch/",
        brain: HybridBrain | None = None,
    ) -> None:
        self.brain = brain if brain else HybridBrain()
        self.rss_url = rss_url

    def check_for_breaking_news(self) -> dict[str, str] | None:
        """
        Scans the RSS feed and asks the Brain if any story is viral-worthy.
        """
        logger.info("📰 Newsroom: Scanning feeds...")

        try:
            feed = feedparser.parse(self.rss_url)
            if not feed.entries:
                logger.warning("⚠️ Newsroom: No entries found in RSS feed.")
                return None

            latest = feed.entries[0]
            title = latest.title

            prompt = (
                f"Analyze this news headline: '{title}'. "
                "Is it viral material? "
                "Return JSON: {'is_viral': true/false, 'hook': 'Viral hook sentence...', 'reason': 'Why...'}"
            )

            res = self.brain.think(prompt, json_mode=True)
            data = json.loads(res)

            if data.get("is_viral"):
                logger.info(f"🔥 Viral News Found: {title}")
                return {
                    "topic": title,
                    "hook": data.get("hook", title),
                    "url": latest.link,
                }

            return None

        except json.JSONDecodeError:
            logger.error("❌ Newsroom: AI returned invalid JSON.")
            return None
        except Exception as e:
            logger.error(f"❌ Newsroom Error: {e}")
            return None
