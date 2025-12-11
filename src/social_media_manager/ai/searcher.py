"""
Web Search Module for AgencyOS.

Provides web search capabilities using DuckDuckGo.
Gives AI agents "eyes" to search for real-time information.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid startup issues
DDGS_AVAILABLE = False
try:
    from duckduckgo_search import DDGS

    DDGS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ duckduckgo-search not installed. Web search disabled.")


class WebSearcher:
    """
    Web search agent using DuckDuckGo.

    Provides real-time web search, news search, and image search
    capabilities for AI agents.
    """

    def __init__(self) -> None:
        """Initialize the WebSearcher."""
        self.available = DDGS_AVAILABLE
        if not self.available:
            logger.warning("❌ WebSearcher unavailable - install duckduckgo-search")

    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
    ) -> list[dict]:
        """
        Perform a web search.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.
            region: Region code (wt-wt = worldwide).

        Returns:
            List of search results with title, href, and body.
        """
        if not self.available:
            return []

        try:
            logger.info(f"🔍 Searching: {query[:50]}...")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region=region, max_results=max_results))
            logger.info(f"✅ Found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def search_news(
        self,
        query: str,
        max_results: int = 5,
        timelimit: str = "w",  # d=day, w=week, m=month
    ) -> list[dict]:
        """
        Search for recent news articles.

        Args:
            query: News search query.
            max_results: Maximum results.
            timelimit: Time filter (d=day, w=week, m=month).

        Returns:
            List of news articles with title, url, body, date.
        """
        if not self.available:
            return []

        try:
            logger.info(f"📰 Searching news: {query[:50]}...")
            with DDGS() as ddgs:
                results = list(
                    ddgs.news(query, timelimit=timelimit, max_results=max_results)
                )
            logger.info(f"✅ Found {len(results)} news articles")
            return results
        except Exception as e:
            logger.error(f"News search failed: {e}")
            return []

    def search_images(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict]:
        """
        Search for images.

        Args:
            query: Image search query.
            max_results: Maximum results.

        Returns:
            List of images with title, image url, thumbnail.
        """
        if not self.available:
            return []

        try:
            logger.info(f"🖼️ Searching images: {query[:50]}...")
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=max_results))
            logger.info(f"✅ Found {len(results)} images")
            return results
        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return []

    def get_instant_answer(self, query: str) -> Optional[str]:
        """
        Get an instant answer for a query (like Wikipedia summary).

        Args:
            query: The question or topic.

        Returns:
            Instant answer text or None.
        """
        if not self.available:
            return None

        try:
            with DDGS() as ddgs:
                results = list(ddgs.answers(query))
                if results:
                    return results[0].get("text", "")
            return None
        except Exception:
            return None

    def research_topic(self, topic: str, depth: int = 3) -> dict:
        """
        Comprehensive research on a topic.

        Combines web search, news, and instant answers.

        Args:
            topic: Topic to research.
            depth: Number of results per category.

        Returns:
            Dictionary with web results, news, and summary.
        """
        logger.info(f"🧠 Researching: {topic}")

        research = {
            "topic": topic,
            "web_results": self.search(topic, max_results=depth),
            "news": self.search_news(topic, max_results=depth),
            "instant_answer": self.get_instant_answer(topic),
        }

        # Create a summary
        snippets = []
        for result in research["web_results"][:2]:
            snippets.append(result.get("body", "")[:200])

        research["summary"] = " ".join(snippets) if snippets else None

        return research

    # === MCP-BASED METHODS ===

    async def search_with_mcp(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict]:
        """
        Search using MCP Brave Search server.

        Falls back to DuckDuckGo if MCP unavailable.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of search results with title, url, description
        """
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            # Check if brave-search server is available
            if "brave-search" not in manager.servers:
                logger.debug("Brave Search MCP not configured, using DDG fallback")
                return self.search(query, max_results)

            logger.info(f"🔍 MCP Search: {query[:50]}...")

            result = await manager.call_tool(
                "brave-search",
                "brave_web_search",
                {"query": query, "count": max_results},
            )

            if "error" in result:
                logger.warning(f"MCP search failed: {result['error']}, using fallback")
                return self.search(query, max_results)

            # Parse Brave results into standard format
            raw_results = result.get("result", [])
            if isinstance(raw_results, str):
                import json

                try:
                    raw_results = json.loads(raw_results)
                except json.JSONDecodeError:
                    return self.search(query, max_results)

            parsed = []
            for item in raw_results[:max_results]:
                parsed.append(
                    {
                        "title": item.get("title", ""),
                        "href": item.get("url", ""),
                        "body": item.get("description", ""),
                    }
                )

            logger.info(f"✅ MCP Found {len(parsed)} results")
            return parsed

        except ImportError:
            logger.warning("MCP client not available, using DDG")
            return self.search(query, max_results)
        except Exception as e:
            logger.error(f"MCP search error: {e}, using fallback")
            return self.search(query, max_results)

    async def research_topic_with_mcp(self, topic: str, depth: int = 3) -> dict:
        """
        Comprehensive research using MCP when available.

        Args:
            topic: Topic to research
            depth: Result depth

        Returns:
            Research dictionary with web results and summary
        """
        logger.info(f"🧠 MCP Research: {topic}")

        web_results = await self.search_with_mcp(topic, max_results=depth)

        research = {
            "topic": topic,
            "web_results": web_results,
            "news": self.search_news(topic, max_results=depth),
            "instant_answer": self.get_instant_answer(topic),
        }

        snippets = [r.get("body", "")[:200] for r in web_results[:2]]
        research["summary"] = " ".join(snippets) if snippets else None

        return research
