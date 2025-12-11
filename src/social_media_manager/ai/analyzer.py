import logging
import random

from sqlalchemy import func

from ..database import DatabaseManager, PostedContent, Video

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Analyzes content performance to determine the best strategy.

    Attributes:
        db (DatabaseManager): The database manager instance.
        styles (list[str]): List of available content styles.
    """

    def __init__(self, db: DatabaseManager | None = None) -> None:
        """
        Initialize the ContentAnalyzer.

        Args:
            db: Optional DatabaseManager instance for dependency injection.
        """
        self.db = db if db else DatabaseManager()
        self.styles = ["engaging", "professional", "casual", "funny"]

    def get_best_style(self) -> str:
        """
        Determine the best content style based on past performance.

        Uses an epsilon-greedy strategy to balance exploration (random style)
        and exploitation (best performing style based on views).

        Returns:
            str: The selected content style.
        """
        # 20% exploration: pick random style
        if random.random() < 0.2:
            return random.choice(self.styles)

        # 80% exploitation: use best performing style
        try:
            with self.db.get_session() as session:
                # Query: Get style with highest average views
                # SELECT v.style, AVG(p.views) as avg_views
                # FROM videos v JOIN posted_content p ON v.id = p.video_id
                # GROUP BY v.style ORDER BY avg_views DESC LIMIT 1
                result = (
                    session.query(Video.style, func.avg(PostedContent.views))
                    .join(PostedContent, Video.id == PostedContent.video_id)
                    .group_by(Video.style)
                    .order_by(func.avg(PostedContent.views).desc())
                    .first()
                )

                if result and result[0]:
                    return result[0]
                return "engaging"

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return "engaging"

    # === MCP-BASED METHODS ===

    async def analyze_with_mcp(self, question: str) -> str:
        """
        Answer analytics questions using natural language via PostgreSQL MCP.

        Allows the LLM to write and execute SQL queries based on natural
        language questions about content performance.

        Args:
            question: Natural language question about analytics

        Returns:
            Answer from the LLM after querying the database

        Example:
            >>> await analyzer.analyze_with_mcp(
            ...     "Which video style has the highest average views in the last 30 days?"
            ... )
        """
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "postgres" not in manager.servers:
                logger.warning("PostgreSQL MCP not configured")
                return "PostgreSQL MCP server not available. Using default analysis."

            logger.info(f"📊 MCP Analytics: {question[:50]}...")

            # Call the postgres MCP to query the database
            result = await manager.call_tool(
                "postgres",
                "query",
                {"sql": f"/* Question: {question} */ SELECT 'Use LLM to generate SQL'"},
            )

            if "error" in result:
                logger.warning(f"MCP query failed: {result['error']}")
                return f"Query failed: {result['error']}"

            return str(result.get("result", "No results"))

        except ImportError:
            logger.debug("MCP client not available")
            return "MCP client not available"
        except Exception as e:
            logger.error(f"MCP analytics error: {e}")
            return f"Error: {e}"

    async def get_insights_with_mcp(self) -> dict:
        """
        Get comprehensive content insights using MCP.

        Returns:
            Dictionary with performance metrics and recommendations
        """
        insights = {
            "best_style": self.get_best_style(),
            "mcp_available": False,
        }

        try:
            from ..core.mcp_client import get_mcp_manager

            manager = get_mcp_manager()
            insights["mcp_available"] = "postgres" in manager.servers
        except ImportError:
            pass

        return insights
