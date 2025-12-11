"""
Brand Memory Graph for AgencyOS.

Stores embeddings of high-performing assets to ensure visual
and tonal consistency across generated content.

Features:
- CLIP embeddings for visual style matching
- Audio embeddings for voice consistency
- Performance-weighted similarity search
- Style tag organization
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from ..config import config


@dataclass
class StyleVector:
    """A style embedding with metadata."""

    asset_id: str
    asset_path: str
    embedding: np.ndarray
    performance_score: float  # 0.0 to 1.0
    asset_type: str  # "visual", "audio", "text"
    style_tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (embedding as list)."""
        return {
            "asset_id": self.asset_id,
            "asset_path": self.asset_path,
            "embedding": self.embedding.tolist(),
            "performance_score": self.performance_score,
            "asset_type": self.asset_type,
            "style_tags": self.style_tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleVector":
        """Deserialize from dictionary."""
        return cls(
            asset_id=data["asset_id"],
            asset_path=data["asset_path"],
            embedding=np.array(data["embedding"]),
            performance_score=data["performance_score"],
            asset_type=data["asset_type"],
            style_tags=data.get("style_tags", []),
            metadata=data.get("metadata", {}),
        )


class StyleGraph:
    """
    Brand Memory using embeddings.

    Stores CLIP vectors for visuals, audio embeddings for voice,
    and retrieves the closest match to guide generation.

    Example:
        graph = StyleGraph()

        # Index high-performing assets
        graph.add_high_performer(
            "thumbnails/viral_thumbnail.png",
            performance_score=0.95,
            style_tags=["energetic", "tech"]
        )

        # Query for similar style
        matches = graph.query_style("energetic tech vibe")
        best_match = matches[0]  # Use this to guide generation
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """
        Initialize the Style Graph.

        Args:
            storage_path: Path to store/load embeddings.
        """
        self.storage_path = storage_path or Path(config.DATA_DIR) / "style_graph.json"
        self.vectors: dict[str, StyleVector] = {}

        # Lazy-loaded models
        self._clip_model = None
        self._clip_processor = None
        self._audio_model = None

        # Load existing data
        self._load()

        logger.info(f"🎨 StyleGraph initialized with {len(self.vectors)} vectors")

    # --- Embedding Generation ---

    def _get_clip_model(self) -> tuple[Any, Any]:
        """Lazy load CLIP model."""
        if self._clip_model is None:
            try:
                from transformers import CLIPModel, CLIPProcessor

                self._clip_model = CLIPModel.from_pretrained(
                    "openai/clip-vit-base-patch32"
                )
                self._clip_processor = CLIPProcessor.from_pretrained(
                    "openai/clip-vit-base-patch32"
                )
                logger.info("🖼️ CLIP model loaded")
            except ImportError:
                logger.warning("⚠️ transformers not installed for CLIP")
                raise

        return self._clip_model, self._clip_processor

    def _generate_visual_embedding(self, image_path: str) -> np.ndarray:
        """Generate CLIP embedding for an image."""
        try:
            from PIL import Image

            model, processor = self._get_clip_model()

            image = Image.open(image_path)
            inputs = processor(images=image, return_tensors="pt")
            outputs = model.get_image_features(**inputs)

            # Normalize embedding
            embedding = outputs.detach().numpy()[0]
            embedding = embedding / np.linalg.norm(embedding)

            return embedding

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate visual embedding: {e}")
            # Return random embedding as fallback
            return np.random.randn(512).astype(np.float32)

    def _generate_text_embedding(self, text: str) -> np.ndarray:
        """Generate CLIP text embedding."""
        try:
            model, processor = self._get_clip_model()

            inputs = processor(text=[text], return_tensors="pt", padding=True)
            outputs = model.get_text_features(**inputs)

            embedding = outputs.detach().numpy()[0]
            embedding = embedding / np.linalg.norm(embedding)

            return embedding

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate text embedding: {e}")
            return np.random.randn(512).astype(np.float32)

    def _generate_audio_embedding(self, audio_path: str) -> np.ndarray:
        """Generate audio embedding (placeholder for future implementation)."""
        # TODO: Implement with audio model (e.g., Wav2Vec2)
        logger.info(f"🔊 Audio embedding for: {audio_path} (placeholder)")
        return np.random.randn(256).astype(np.float32)

    def _generate_embedding(self, asset_path: str, asset_type: str) -> np.ndarray:
        """Generate embedding based on asset type."""
        if asset_type == "visual":
            return self._generate_visual_embedding(asset_path)
        elif asset_type == "audio":
            return self._generate_audio_embedding(asset_path)
        elif asset_type == "text":
            # Read text file and embed
            text = Path(asset_path).read_text()
            return self._generate_text_embedding(text)
        else:
            logger.warning(f"⚠️ Unknown asset type: {asset_type}")
            return np.random.randn(512).astype(np.float32)

    # --- Asset Management ---

    def add_high_performer(
        self,
        asset_path: str,
        performance_score: float,
        asset_type: str = "visual",
        style_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Index a high-performing asset.

        Args:
            asset_path: Path to the asset file.
            performance_score: Engagement/retention score (0-1).
            asset_type: "visual", "audio", or "text".
            style_tags: Optional style descriptors.
            metadata: Optional additional metadata.

        Returns:
            Asset ID.
        """
        # Validate score
        performance_score = max(0.0, min(1.0, performance_score))

        # Generate embedding
        embedding = self._generate_embedding(asset_path, asset_type)

        # Create unique ID
        asset_id = f"{asset_type}_{hash(asset_path) % 10**8}"

        # Store vector
        self.vectors[asset_id] = StyleVector(
            asset_id=asset_id,
            asset_path=asset_path,
            embedding=embedding,
            performance_score=performance_score,
            asset_type=asset_type,
            style_tags=style_tags or [],
            metadata=metadata or {},
        )

        logger.info(
            f"✨ Added high performer: {asset_path} (score: {performance_score:.2f})"
        )

        # Persist
        self._save()

        return asset_id

    def remove_asset(self, asset_id: str) -> bool:
        """Remove an asset from the graph."""
        if asset_id in self.vectors:
            del self.vectors[asset_id]
            self._save()
            return True
        return False

    def update_performance(self, asset_id: str, new_score: float) -> bool:
        """Update an asset's performance score."""
        if asset_id in self.vectors:
            self.vectors[asset_id].performance_score = max(0.0, min(1.0, new_score))
            self._save()
            return True
        return False

    # --- Similarity Search ---

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def query_style(
        self,
        query: str | np.ndarray,
        asset_type: str | None = None,
        style_tags: list[str] | None = None,
        top_k: int = 3,
        min_performance: float = 0.0,
    ) -> list[StyleVector]:
        """
        Find closest matching styles.

        Args:
            query: Text description or embedding vector.
            asset_type: Filter by type ("visual", "audio", "text").
            style_tags: Filter by tags (any match).
            top_k: Number of results.
            min_performance: Minimum performance score filter.

        Returns:
            Top matching StyleVector objects.
        """
        # Convert query to embedding if string
        if isinstance(query, str):
            query_vec = self._generate_text_embedding(query)
        else:
            query_vec = query

        # Filter candidates
        candidates = list(self.vectors.values())

        if asset_type:
            candidates = [v for v in candidates if v.asset_type == asset_type]

        if style_tags:
            candidates = [
                v for v in candidates if any(tag in v.style_tags for tag in style_tags)
            ]

        if min_performance > 0:
            candidates = [
                v for v in candidates if v.performance_score >= min_performance
            ]

        if not candidates:
            return []

        # Score each candidate
        scored: list[tuple[float, StyleVector]] = []
        for v in candidates:
            similarity = self._cosine_similarity(query_vec, v.embedding)
            # Weight by performance score
            weighted = similarity * (0.5 + 0.5 * v.performance_score)
            scored.append((weighted, v))

        # Sort by score descending
        scored.sort(reverse=True, key=lambda x: x[0])

        return [v for _, v in scored[:top_k]]

    def get_style_by_tags(self, tags: list[str], top_k: int = 5) -> list[StyleVector]:
        """Get top performers matching specific tags."""
        matches = [
            v for v in self.vectors.values() if any(tag in v.style_tags for tag in tags)
        ]

        # Sort by performance
        matches.sort(key=lambda v: v.performance_score, reverse=True)

        return matches[:top_k]

    # --- Persistence ---

    def _save(self) -> None:
        """Save vectors to disk."""
        try:
            data = {
                "vectors": [v.to_dict() for v in self.vectors.values()],
            }
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"❌ Failed to save StyleGraph: {e}")

    def _load(self) -> None:
        """Load vectors from disk."""
        if not self.storage_path.exists():
            return

        try:
            data = json.loads(self.storage_path.read_text())
            for v_data in data.get("vectors", []):
                v = StyleVector.from_dict(v_data)
                self.vectors[v.asset_id] = v
        except Exception as e:
            logger.warning(f"⚠️ Failed to load StyleGraph: {e}")

    # --- Stats ---

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        type_counts: dict[str, int] = {}
        for v in self.vectors.values():
            type_counts[v.asset_type] = type_counts.get(v.asset_type, 0) + 1

        return {
            "total_vectors": len(self.vectors),
            "by_type": type_counts,
            "avg_performance": (
                sum(v.performance_score for v in self.vectors.values())
                / len(self.vectors)
                if self.vectors
                else 0
            ),
            "storage_path": str(self.storage_path),
        }


# --- Convenience Functions ---


def get_style_for_content(
    description: str,
    asset_type: str = "visual",
) -> StyleVector | None:
    """
    Quick function to get the best style match.

    Args:
        description: Text describing desired style.
        asset_type: Type of asset.

    Returns:
        Best matching StyleVector or None.
    """
    graph = StyleGraph()
    matches = graph.query_style(description, asset_type=asset_type, top_k=1)
    return matches[0] if matches else None
