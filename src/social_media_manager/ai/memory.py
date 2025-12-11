import logging
from datetime import datetime

import chromadb

from ..config import config

logger = logging.getLogger(__name__)


class ContentMemory:
    """
    Persistent memory for content history using ChromaDB.

    Stores previously generated posts to avoid repetition and provide context.
    """

    def __init__(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(path=str(config.MEMORY_PATH))
            self.collection = self.client.get_or_create_collection(name="post_history")
        except Exception as e:
            logger.error(f"❌ ContentMemory: Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def save_post(self, topic: str, caption: str, platform: str) -> bool:
        """
        Save a generated post to memory.

        Args:
            topic: The topic of the post.
            caption: The generated caption text.
            platform: Social media platform name.

        Returns:
            True if saved successfully, False otherwise.
        """
        if not self.client or not self.collection:
            logger.warning("⚠️ ContentMemory: Cannot save - not initialized")
            return False

        try:
            ts = datetime.now().isoformat()
            self.collection.add(
                documents=[caption],
                metadatas=[{"topic": topic, "platform": platform, "date": ts}],
                ids=[f"post_{hash(topic)}_{ts}"],
            )
            return True
        except Exception as e:
            logger.error(f"❌ ContentMemory: Failed to save post: {e}")
            return False

    def recall_context(self, topic: str) -> str:
        """
        Recall historical context for a topic.

        Args:
            topic: The topic to search for.

        Returns:
            Historical context string, or empty string if not found.
        """
        if not self.client or not self.collection:
            return ""

        try:
            res = self.collection.query(query_texts=[topic], n_results=1)
            if res and res.get("documents") and res["documents"][0]:
                return f"HISTORY: {res['documents'][0][0]}"
            return ""
        except Exception as e:
            logger.error(f"❌ ContentMemory: Failed to recall context: {e}")
            return ""

    # === MCP-BASED METHODS ===

    async def recall_with_mcp(self, topic: str) -> str:
        """
        Recall context using MCP Memory server.

        Falls back to direct ChromaDB if MCP unavailable.

        Args:
            topic: Topic to search for

        Returns:
            Historical context string
        """
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "memory" not in manager.servers:
                logger.debug("Memory MCP not configured, using direct ChromaDB")
                return self.recall_context(topic)

            logger.info(f"🧠 MCP Recall: {topic[:50]}...")

            result = await manager.call_tool(
                "memory", "retrieve_memory", {"query": topic}
            )

            if "error" in result:
                logger.warning(f"MCP recall failed: {result['error']}")
                return self.recall_context(topic)

            content = result.get("result", "")
            if content:
                return f"HISTORY: {content}"
            return ""

        except ImportError:
            logger.debug("MCP client not available")
            return self.recall_context(topic)
        except Exception as e:
            logger.error(f"MCP recall error: {e}")
            return self.recall_context(topic)

    async def save_with_mcp(self, topic: str, caption: str, platform: str) -> bool:
        """
        Save to memory using MCP Memory server.

        Falls back to direct ChromaDB if MCP unavailable.
        """
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "memory" not in manager.servers:
                return self.save_post(topic, caption, platform)

            result = await manager.call_tool(
                "memory",
                "store_memory",
                {
                    "content": caption,
                    "metadata": {"topic": topic, "platform": platform},
                },
            )

            if "error" in result:
                return self.save_post(topic, caption, platform)

            return True

        except Exception:
            return self.save_post(topic, caption, platform)
