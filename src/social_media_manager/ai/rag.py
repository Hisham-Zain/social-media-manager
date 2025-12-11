import logging
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from ..config import config  # <--- IMPORT CONFIG

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    RAG Engine for the Community Agent.
    """

    def __init__(self, client_name: str = "default"):
        self.client_name = client_name
        # FIX: Use config.MEMORY_PATH
        self.chroma_client = chromadb.PersistentClient(path=str(config.MEMORY_PATH))

        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=f"knowledge_{client_name}", embedding_function=self.embedding_fn
        )

    def add_document(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> None:
        try:
            doc_id = str(hash(text))
            self.collection.add(
                documents=[text],
                metadatas=[metadata] if metadata else None,
                ids=[doc_id],
            )
            logger.info(f"📚 Added to Knowledge Base: {text[:30]}...")
        except Exception as e:
            logger.error(f"RAG Add Error: {e}")

    def query(self, query_text: str, n_results: int = 3) -> list[str]:
        try:
            results = self.collection.query(
                query_texts=[query_text], n_results=n_results
            )
            if results and results["documents"]:
                return results["documents"][0]
            return []
        except Exception as e:
            logger.error(f"RAG Query Error: {e}")
            return []
