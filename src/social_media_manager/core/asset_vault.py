"""
AssetVault: Smart Asset Management for AgencyOS.

Provides centralized storage, deduplication, and semantic search for all media assets.
"""

import hashlib
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from ..database import Asset, DatabaseManager


class AssetVault:
    """
    The Vault: Centralized asset management with AI-powered organization.

    Features:
    - Automatic deduplication via content hashing
    - AI-powered tagging using CLIP embeddings
    - Semantic search across all assets
    - Project associations

    Example:
        vault = AssetVault()

        # Register a new asset
        asset_id = vault.register("/path/to/image.jpg", source="generated")

        # Search semantically
        results = vault.search("sunset over mountains", limit=5)

        # Find duplicates
        duplicates = vault.find_duplicates("/path/to/new_file.jpg")
    """

    SUPPORTED_TYPES = {
        "image": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"],
        "video": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"],
        "audio": [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"],
        "document": [".pdf", ".txt", ".md", ".json", ".csv"],
    }

    def __init__(self, db: DatabaseManager | None = None) -> None:
        """Initialize the vault."""
        self.db = db or DatabaseManager()
        self._visual_rag = None  # Lazy load

    @property
    def visual_rag(self):
        """Lazy-load VisualRAG for embedding generation."""
        if self._visual_rag is None:
            try:
                from ..ai.visual_rag import VisualRAG

                self._visual_rag = VisualRAG()
            except ImportError:
                logger.warning("⚠️ VisualRAG not available for auto-tagging")
        return self._visual_rag

    def register(
        self,
        filepath: str | Path,
        source: str = "uploaded",
        tags: list[str] | None = None,
        project_id: int | None = None,
        auto_tag: bool = True,
    ) -> int | None:
        """
        Register an asset in the vault.

        Args:
            filepath: Path to the asset file.
            source: Origin of asset (uploaded, generated, stock).
            tags: Manual tags.
            project_id: Associated project ID.
            auto_tag: If True, generate AI tags using CLIP.

        Returns:
            Asset ID, or None if registration failed.
        """
        path = Path(filepath)

        if not path.exists():
            logger.error(f"❌ Asset file not found: {filepath}")
            return None

        # Determine asset type
        asset_type = self._get_asset_type(path)
        if not asset_type:
            logger.warning(f"⚠️ Unsupported file type: {path.suffix}")
            asset_type = "document"  # Fallback

        # Calculate content hash for deduplication
        content_hash = self._hash_file(path)

        # Check for duplicate
        existing = self._find_by_hash(content_hash)
        if existing:
            logger.info(f"ℹ️ Asset already exists (ID: {existing['id']})")
            return existing["id"]

        # Get file metadata
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))

        # Get dimensions for images/videos
        width, height, duration = self._get_media_info(path, asset_type)

        # Generate AI tags if requested
        description = None
        embedding = None
        if auto_tag and asset_type in ["image", "video"] and self.visual_rag:
            try:
                description, embedding = self._generate_embedding(path, asset_type)
            except Exception as e:
                logger.warning(f"⚠️ Auto-tagging failed: {e}")

        # Combine manual and AI tags
        all_tags = list(tags or [])
        if description:
            all_tags.append(description[:50])  # Add short description as tag

        # Register in database
        with self.db.get_session() as session:
            asset = Asset(
                filename=path.name,
                filepath=str(path.absolute()),
                asset_type=asset_type,
                file_size=stat.st_size,
                mime_type=mime_type,
                duration=duration,
                width=width,
                height=height,
                content_hash=content_hash,
                tags=json.dumps(all_tags) if all_tags else None,
                source=source,
                project_id=project_id,
                description=description,
                embedding=json.dumps(embedding) if embedding else None,
                indexed_at=datetime.now().isoformat() if embedding else None,
            )
            session.add(asset)
            session.flush()
            asset_id = asset.id

        logger.info(f"✅ Registered asset: {path.name} (ID: {asset_id})")
        return asset_id

    def search(
        self,
        query: str,
        asset_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search assets semantically or by metadata.

        Args:
            query: Text query for semantic search.
            asset_type: Filter by type (image, video, audio).
            tags: Filter by tags.
            limit: Maximum results.

        Returns:
            List of matching asset dicts with similarity scores.
        """

        results = []

        # First, try semantic search if VisualRAG is available
        if self.visual_rag and query:
            try:
                # Generate query embedding
                query_embedding = self._get_text_embedding(query)
                if query_embedding:
                    results = self._semantic_search(query_embedding, asset_type, limit)
            except Exception as e:
                logger.warning(f"⚠️ Semantic search failed: {e}")

        # Fallback or supplement with keyword search
        if not results or len(results) < limit:
            keyword_results = self._keyword_search(
                query, asset_type, tags, limit - len(results)
            )
            # Merge results
            existing_ids = {r["id"] for r in results}
            for r in keyword_results:
                if r["id"] not in existing_ids:
                    results.append(r)

        return results[:limit]

    def find_duplicates(self, filepath: str | Path) -> list[dict[str, Any]]:
        """
        Find existing duplicates of a file.

        Args:
            filepath: Path to file to check.

        Returns:
            List of matching assets with same content hash.
        """
        path = Path(filepath)
        if not path.exists():
            return []

        content_hash = self._hash_file(path)
        return self._find_all_by_hash(content_hash)

    def get_asset(self, asset_id: int) -> dict[str, Any] | None:
        """Get asset by ID."""
        with self.db.get_session() as session:
            asset = session.get(Asset, asset_id)
            if not asset:
                return None
            return self._asset_to_dict(asset)

    def delete_asset(self, asset_id: int, delete_file: bool = False) -> bool:
        """
        Delete asset from vault.

        Args:
            asset_id: Asset ID to delete.
            delete_file: If True, also delete the physical file.

        Returns:
            True if deleted.
        """
        with self.db.get_session() as session:
            asset = session.get(Asset, asset_id)
            if not asset:
                return False

            if delete_file:
                try:
                    Path(asset.filepath).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete file: {e}")

            session.delete(asset)
            logger.info(f"🗑️ Deleted asset ID: {asset_id}")
            return True

    def update_tags(self, asset_id: int, tags: list[str]) -> bool:
        """Update asset tags."""
        with self.db.get_session() as session:
            asset = session.get(Asset, asset_id)
            if not asset:
                return False
            asset.tags = json.dumps(tags)
            return True

    def get_stats(self) -> dict[str, Any]:
        """Get vault statistics."""
        from sqlalchemy import func, select

        with self.db.get_session() as session:
            total = session.execute(select(func.count(Asset.id))).scalar() or 0
            total_size = (
                session.execute(select(func.sum(Asset.file_size))).scalar() or 0
            )

            by_type = {}
            for asset_type in ["image", "video", "audio", "document"]:
                count = (
                    session.execute(
                        select(func.count(Asset.id)).where(
                            Asset.asset_type == asset_type
                        )
                    ).scalar()
                    or 0
                )
                by_type[asset_type] = count

            indexed = (
                session.execute(
                    select(func.count(Asset.id)).where(Asset.embedding.isnot(None))
                ).scalar()
                or 0
            )

        return {
            "total_assets": total,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": by_type,
            "indexed_count": indexed,
        }

    # --- Private Methods ---

    def _get_asset_type(self, path: Path) -> str | None:
        """Determine asset type from file extension."""
        ext = path.suffix.lower()
        for asset_type, extensions in self.SUPPORTED_TYPES.items():
            if ext in extensions:
                return asset_type
        return None

    def _hash_file(self, path: Path, chunk_size: int = 8192) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _find_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        """Find asset by content hash."""
        from sqlalchemy import select

        with self.db.get_session() as session:
            stmt = select(Asset).where(Asset.content_hash == content_hash)
            asset = session.execute(stmt).scalars().first()
            if asset:
                return self._asset_to_dict(asset)
        return None

    def _find_all_by_hash(self, content_hash: str) -> list[dict[str, Any]]:
        """Find all assets with matching hash."""
        from sqlalchemy import select

        with self.db.get_session() as session:
            stmt = select(Asset).where(Asset.content_hash == content_hash)
            assets = session.execute(stmt).scalars().all()
            return [self._asset_to_dict(a) for a in assets]

    def _get_media_info(
        self, path: Path, asset_type: str
    ) -> tuple[int | None, int | None, float | None]:
        """Get dimensions and duration for media files."""
        width = height = duration = None

        if asset_type == "image":
            try:
                from PIL import Image

                with Image.open(path) as img:
                    width, height = img.size
            except Exception:
                pass

        elif asset_type == "video":
            try:
                from moviepy import VideoFileClip

                clip = VideoFileClip(str(path))
                width, height = clip.size
                duration = clip.duration
                clip.close()
            except Exception:
                pass

        elif asset_type == "audio":
            try:
                from moviepy import AudioFileClip

                clip = AudioFileClip(str(path))
                duration = clip.duration
                clip.close()
            except Exception:
                pass

        return width, height, duration

    def _generate_embedding(
        self, path: Path, asset_type: str
    ) -> tuple[str | None, list[float] | None]:
        """Generate CLIP embedding and description for asset."""
        if not self.visual_rag:
            return None, None

        try:
            if asset_type == "image":
                # Use CLIP to get embedding
                embedding = self.visual_rag.get_image_embedding(str(path))
                # Generate description (simplified)
                description = (
                    self.visual_rag.describe_image(str(path))
                    if hasattr(self.visual_rag, "describe_image")
                    else None
                )
                return (
                    description,
                    embedding.tolist() if embedding is not None else None,
                )
            elif asset_type == "video":
                # Index video and get first frame embedding
                self.visual_rag.index_video(str(path))
                return None, None
        except Exception as e:
            logger.debug(f"Embedding generation error: {e}")

        return None, None

    def _get_text_embedding(self, text: str) -> list[float] | None:
        """Get CLIP text embedding."""
        if not self.visual_rag:
            return None
        try:
            embedding = self.visual_rag.get_text_embedding(text)
            return embedding.tolist() if embedding is not None else None
        except Exception:
            return None

    def _semantic_search(
        self,
        query_embedding: list[float],
        asset_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search by embedding similarity."""
        import numpy as np
        from sqlalchemy import select

        results = []
        query_np = np.array(query_embedding)

        with self.db.get_session() as session:
            stmt = select(Asset).where(Asset.embedding.isnot(None))
            if asset_type:
                stmt = stmt.where(Asset.asset_type == asset_type)

            assets = session.execute(stmt).scalars().all()

            for asset in assets:
                try:
                    asset_embedding = np.array(json.loads(asset.embedding))
                    # Cosine similarity
                    similarity = np.dot(query_np, asset_embedding) / (
                        np.linalg.norm(query_np) * np.linalg.norm(asset_embedding)
                    )
                    results.append(
                        {
                            **self._asset_to_dict(asset),
                            "similarity": float(similarity),
                        }
                    )
                except Exception:
                    continue

        # Sort by similarity
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return results[:limit]

    def _keyword_search(
        self,
        query: str,
        asset_type: str | None,
        tags: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Simple keyword search in filename, description, tags."""
        from sqlalchemy import or_, select

        with self.db.get_session() as session:
            stmt = select(Asset)

            if asset_type:
                stmt = stmt.where(Asset.asset_type == asset_type)

            if query:
                stmt = stmt.where(
                    or_(
                        Asset.filename.ilike(f"%{query}%"),
                        Asset.description.ilike(f"%{query}%"),
                        Asset.tags.ilike(f"%{query}%"),
                    )
                )

            if tags:
                for tag in tags:
                    stmt = stmt.where(Asset.tags.ilike(f"%{tag}%"))

            stmt = stmt.limit(limit)
            assets = session.execute(stmt).scalars().all()
            return [self._asset_to_dict(a) for a in assets]

    def _asset_to_dict(self, asset: Asset) -> dict[str, Any]:
        """Convert Asset ORM to dict."""
        return {
            "id": asset.id,
            "filename": asset.filename,
            "filepath": asset.filepath,
            "asset_type": asset.asset_type,
            "file_size": asset.file_size,
            "mime_type": asset.mime_type,
            "duration": asset.duration,
            "width": asset.width,
            "height": asset.height,
            "content_hash": asset.content_hash,
            "tags": json.loads(asset.tags) if asset.tags else [],
            "source": asset.source,
            "project_id": asset.project_id,
            "description": asset.description,
            "created_at": asset.created_at,
            "indexed_at": asset.indexed_at,
        }


# Singleton
_vault: AssetVault | None = None


def get_asset_vault() -> AssetVault:
    """Get the AssetVault singleton."""
    global _vault
    if _vault is None:
        _vault = AssetVault()
    return _vault
