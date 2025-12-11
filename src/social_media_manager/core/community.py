import logging

from ..ai.brain import HybridBrain
from ..ai.rag import KnowledgeBase
from ..config import config
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class CommunityManager:
    """Manages community interactions and generates AI-powered replies."""

    def __init__(
        self, db: DatabaseManager | None = None, brain: HybridBrain | None = None
    ) -> None:
        self.db = db if db else DatabaseManager()
        self.brain = brain if brain else HybridBrain()
        self.creds_path = config.CREDS_DIR
        self.rag: KnowledgeBase | None = None
        try:
            self.rag = KnowledgeBase()
        except Exception as e:
            logger.warning(f"⚠️ KnowledgeBase unavailable: {e}")
            self.rag = None

    def fetch_youtube_comments(self) -> int:
        """Fetch comments from YouTube (placeholder)."""
        return 0

    def generate_replies(self) -> None:
        """Generate AI-powered replies for pending comments."""
        df = self.db.get_pending_comments()
        if df.empty:
            return
        for _, row in df.iterrows():
            context = self.rag.query(row["text"]) if self.rag else ""
            reply = self.brain.think(f"Reply to: '{row['text']}'. Context: {context}")
            if reply:
                self.db.update_comment_reply(row["id"], reply)
