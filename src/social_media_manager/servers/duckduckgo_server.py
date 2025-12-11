#!/usr/bin/env python3
"""
DuckDuckGo Search MCP Server

A local FOSS MCP server providing web search via DuckDuckGo.
Cost: $0 - No API key required.
"""

import logging

from duckduckgo_search import DDGS
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("DuckDuckGo Search")


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo (free, no API key required).

    Args:
        query: Search query string
        max_results: Maximum number of results (default 5)

    Returns:
        JSON-formatted search results with title, link, and snippet
    """
    logger.info(f"🔍 Searching: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        formatted = []
        for r in results:
            formatted.append(
                {
                    "title": r.get("title", ""),
                    "link": r.get("link", r.get("href", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                }
            )

        return str(formatted)
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error: {e}"


@mcp.tool()
def search_news(query: str, max_results: int = 5) -> str:
    """
    Search news articles using DuckDuckGo.

    Args:
        query: News search query
        max_results: Maximum number of results

    Returns:
        JSON-formatted news results
    """
    logger.info(f"📰 Searching news: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        return str(results)
    except Exception as e:
        logger.error(f"News search error: {e}")
        return f"Error: {e}"


@mcp.tool()
def search_images(query: str, max_results: int = 5) -> str:
    """
    Search images using DuckDuckGo.

    Args:
        query: Image search query
        max_results: Maximum number of results

    Returns:
        JSON-formatted image results with URLs
    """
    logger.info(f"🖼️ Searching images: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=max_results))

        formatted = []
        for r in results:
            formatted.append(
                {
                    "title": r.get("title", ""),
                    "image": r.get("image", ""),
                    "thumbnail": r.get("thumbnail", ""),
                    "source": r.get("source", ""),
                }
            )
        return str(formatted)
    except Exception as e:
        logger.error(f"Image search error: {e}")
        return f"Error: {e}"


if __name__ == "__main__":
    logger.info("🦆 Starting DuckDuckGo MCP Server...")
    mcp.run()
