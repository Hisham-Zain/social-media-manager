import logging
from typing import Any

logger = logging.getLogger(__name__)


class AffiliateScout:
    """
    Scans content for monetization triggers.
    """

    def __init__(self) -> None:
        self.affiliate_map = {
            "hosting": {"link": "hostinger.com/go", "icon": "🌐"},
            "vpn": {"link": "nordvpn.com/promo", "icon": "🔒"},
            "camera": {"link": "amzn.to/sony-a7s", "icon": "📸"},
            "gpu": {"link": "nvidia.com", "icon": "🎮"},
            "ai": {"link": "jasper.ai", "icon": "🤖"},
            "crypto": {"link": "coinbase.com/join", "icon": "🪙"},
        }

    def scan(self, text: str) -> dict[str, Any]:
        """
        Returns actionable match data for the video processor.
        """
        found_matches: list[dict[str, str]] = []
        text_lower = text.lower()

        for keyword, data in self.affiliate_map.items():
            if keyword in text_lower:
                found_matches.append(
                    {"keyword": keyword, "link": data["link"], "icon": data["icon"]}
                )

        if found_matches:
            logger.info(f"💰 Monetizer found {len(found_matches)} opportunities.")
            return {
                "status": f"💰 Active: {len(found_matches)} overlays",
                "matches": found_matches,
            }
        return {"status": "✅ Clean", "matches": []}
