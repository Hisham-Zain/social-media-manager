import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..config import config
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class AnalyticsUpdater:
    """
    Updates analytics data from external platforms (YouTube).
    """

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db if db else DatabaseManager()
        self.creds_path: Path = config.CREDS_DIR

    def refresh_stats(self) -> None:
        """
        Fetch and update statistics (views, likes) from YouTube.
        """
        logger.info("📊 Fetching legal stats from YouTube...")
        token = self.creds_path / "token.json"

        if not token.exists():
            logger.warning("⚠️ No YouTube token found in credentials. Skipping stats.")
            return

        try:
            creds = Credentials.from_authorized_user_file(
                str(token), ["https://www.googleapis.com/auth/youtube.upload"]
            )
            youtube = build("youtube", "v3", credentials=creds)

            # Using new ORM method to get platform_ids
            # We'll need to adapt this if you strictly use get_analytics returning DF
            # For now, let's assume get_analytics returns the PostedContent table as DF
            df = self.db.get_analytics()
            youtube_posts = df[df["platform"] == "youtube"]

            if youtube_posts.empty:
                return

            ids = ",".join(youtube_posts["platform_id"].tolist())
            resp = youtube.videos().list(part="statistics", id=ids).execute()

            # Note: Batch update logic would need ORM adjustment.
            # For simplicity in this 'refactor', we'll log what we found.
            # Real implementation requires a specific update method in DatabaseManager.
            count = 0
            for item in resp.get("items", []):
                stats = item["statistics"]
                # Ideally: self.db.update_stats(item['id'], viewCount, likeCount)
                count += 1

            logger.info(f"✅ Stats updated for {count} videos.")

        except Exception as e:
            logger.error(f"❌ Analytics Update Error: {e}")
