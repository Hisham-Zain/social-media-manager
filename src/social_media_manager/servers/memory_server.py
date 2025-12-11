#!/usr/bin/env python3
"""
ChromaDB Memory MCP Server

A local FOSS MCP server for vector memory using ChromaDB.
Cost: $0 - Uses local ChromaDB storage.

This wraps your existing brain_data/chroma.sqlite3 and makes it
accessible via MCP tools.
"""

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("ChromaDB Memory")

# ChromaDB setup
BRAIN_DATA_DIR = Path(os.getenv("BRAIN_DATA_DIR", "./brain_data"))
BRAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)

_client = None
_collection = None


def _get_collection():
    """Lazy-load ChromaDB collection."""
    global _client, _collection

    if _collection is None:
        try:
            import chromadb
            from chromadb.config import Settings

            _client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(BRAIN_DATA_DIR),
                    anonymized_telemetry=False,
                )
            )

            # Get or create the main collection
            _collection = _client.get_or_create_collection(
                name="agent_memory", metadata={"description": "Agent long-term memory"}
            )
            logger.info(
                f"✅ Loaded ChromaDB collection with {_collection.count()} memories"
            )

        except Exception as e:
            logger.error(f"ChromaDB init error: {e}")
            # Try simpler init for newer chromadb versions
            try:
                import chromadb

                _client = chromadb.PersistentClient(path=str(BRAIN_DATA_DIR))
                _collection = _client.get_or_create_collection(name="agent_memory")
                logger.info(
                    f"✅ Loaded ChromaDB (v2) with {_collection.count()} memories"
                )
            except Exception as e2:
                logger.error(f"ChromaDB v2 init error: {e2}")
                raise

    return _collection


@mcp.tool()
def save_memory(
    text: str,
    category: str = "general",
    metadata: dict | None = None,
) -> str:
    """
    Save a memory to the vector store.

    Args:
        text: The text content to remember
        category: Category for organization (e.g., 'hooks', 'guidelines', 'scripts')
        metadata: Optional additional metadata

    Returns:
        Confirmation message with memory ID
    """
    logger.info(f"💾 Saving memory: {text[:50]}...")

    try:
        import uuid
        from datetime import datetime

        collection = _get_collection()
        memory_id = str(uuid.uuid4())[:8]

        doc_metadata = {
            "category": category,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        collection.add(documents=[text], metadatas=[doc_metadata], ids=[memory_id])

        logger.info(f"✅ Saved memory: {memory_id}")
        return f"Saved memory with ID: {memory_id}"

    except Exception as e:
        logger.error(f"Save error: {e}")
        return f"Error: {e}"


@mcp.tool()
def recall_memory(
    query: str,
    n_results: int = 5,
    category: str | None = None,
) -> str:
    """
    Recall relevant memories based on a query.

    Args:
        query: Search query for semantic similarity
        n_results: Number of results to return
        category: Optional category filter

    Returns:
        JSON-formatted list of relevant memories
    """
    logger.info(f"🧠 Recalling: {query[:50]}...")

    try:
        collection = _get_collection()

        where_filter = {"category": category} if category else None

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        memories = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                memories.append(
                    {
                        "content": doc,
                        "category": meta.get("category", "unknown"),
                        "timestamp": meta.get("timestamp", ""),
                    }
                )

        logger.info(f"✅ Found {len(memories)} memories")
        return str(memories)

    except Exception as e:
        logger.error(f"Recall error: {e}")
        return f"Error: {e}"


@mcp.tool()
def list_categories() -> str:
    """
    List all memory categories in the store.

    Returns:
        List of unique categories
    """
    try:
        collection = _get_collection()

        # Get all metadata
        all_data = collection.get()
        categories = set()

        if all_data.get("metadatas"):
            for meta in all_data["metadatas"]:
                if meta and meta.get("category"):
                    categories.add(meta["category"])

        return str(list(categories))

    except Exception as e:
        logger.error(f"List error: {e}")
        return f"Error: {e}"


@mcp.tool()
def memory_count() -> str:
    """
    Get the total number of memories stored.

    Returns:
        Count of memories
    """
    try:
        collection = _get_collection()
        count = collection.count()
        return f"Total memories: {count}"
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    logger.info("🧠 Starting ChromaDB Memory MCP Server...")
    mcp.run()
