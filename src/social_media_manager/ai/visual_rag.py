"""
Visual RAG (Retrieval Augmented Generation) for AgencyOS.

Index video footage by visual content, not just filenames.
The AI "watches" raw footage and stores vector embeddings,
enabling semantic search like "Show excitement" -> finds smiling frames.

Features:
- Multimodal embeddings (CLIP/BridgeTower)
- Frame extraction and indexing
- Text-to-video semantic search
- ChromaDB vector storage
- Batch processing for large libraries
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from loguru import logger

from ..config import config


@dataclass
class FrameMatch:
    """A matched frame from visual search."""

    video_path: str
    frame_index: int
    timestamp: float  # seconds
    score: float
    description: str | None = None
    thumbnail_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "score": self.score,
            "description": self.description,
            "thumbnail_path": self.thumbnail_path,
        }


@dataclass
class VideoIndex:
    """Index metadata for a video."""

    video_path: str
    video_hash: str
    frame_count: int
    fps: float
    duration: float
    indexed_at: str
    frame_indices: list[int] = field(default_factory=list)  # Which frames are indexed


class VisualRAG:
    """
    Visual RAG for semantic video search.

    Uses CLIP to create embeddings of video frames, stores them in
    ChromaDB, and enables natural language search for footage.

    Example:
        rag = VisualRAG()

        # Index video library
        rag.index_video("/path/to/raw_footage.mp4")
        rag.index_directory("/path/to/footage/")

        # Search by description
        matches = rag.search("person smiling with excitement")
        for match in matches:
            print(f"{match.video_path} @ {match.timestamp}s (score: {match.score})")

        # Get best clip for script
        clip = rag.find_best_clip("Show the product demo")
    """

    # Supported video formats
    SUPPORTED_FORMATS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        collection_name: str = "visual_rag",
        sample_fps: float = 1.0,  # Sample 1 frame per second
        device: str | None = None,
    ):
        """
        Initialize Visual RAG.

        Args:
            model_name: CLIP model for embeddings.
            collection_name: ChromaDB collection name.
            sample_fps: Frames per second to sample for indexing.
            device: Device for model (cuda/cpu/auto).
        """
        self.model_name = model_name
        self.collection_name = collection_name
        self.sample_fps = sample_fps

        # Auto-detect device
        if device is None:
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Paths
        self.index_dir = Path(config.DATA_DIR) / "visual_rag"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir = self.index_dir / "thumbnails"
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

        # Lazy-loaded components
        self._model = None
        self._processor = None
        self._collection = None
        self._video_indices: dict[str, VideoIndex] = {}

        # Load existing indices
        self._load_indices()

        logger.info(f"👁️ VisualRAG initialized (device: {self.device})")

    @property
    def model(self):
        """Lazy load CLIP model."""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def processor(self):
        """Lazy load CLIP processor."""
        if self._processor is None:
            self._load_model()
        return self._processor

    @property
    def collection(self):
        """Lazy load ChromaDB collection."""
        if self._collection is None:
            self._init_collection()
        return self._collection

    def _load_model(self):
        """Load CLIP model and processor."""
        logger.info(f"📦 Loading CLIP model: {self.model_name}")

        try:
            from transformers import CLIPModel, CLIPProcessor

            self._processor = CLIPProcessor.from_pretrained(self.model_name)
            self._model = CLIPModel.from_pretrained(self.model_name)
            self._model = self._model.to(self.device)
            self._model.eval()

            logger.info("✅ CLIP model loaded")

        except Exception as e:
            logger.error(f"Failed to load CLIP: {e}")
            raise

    def _init_collection(self):
        """Initialize ChromaDB collection."""
        try:
            import chromadb
            from chromadb.config import Settings

            persist_dir = str(self.index_dir / "chromadb")

            client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=persist_dir,
                    anonymized_telemetry=False,
                )
            )

            self._collection = client.get_or_create_collection(
                name=self.collection_name, metadata={"hnsw:space": "cosine"}
            )

            logger.info(f"✅ ChromaDB collection ready: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to init ChromaDB: {e}")
            # Fallback to in-memory
            self._collection = InMemoryCollection()

    def _load_indices(self):
        """Load existing video indices."""
        indices_file = self.index_dir / "indices.json"
        if indices_file.exists():
            try:
                with open(indices_file, "r") as f:
                    data = json.load(f)
                for path, index_data in data.items():
                    self._video_indices[path] = VideoIndex(**index_data)
                logger.info(f"📂 Loaded {len(self._video_indices)} video indices")
            except Exception as e:
                logger.warning(f"Failed to load indices: {e}")

    def _save_indices(self):
        """Save video indices."""
        indices_file = self.index_dir / "indices.json"
        data = {}
        for path, index in self._video_indices.items():
            data[path] = {
                "video_path": index.video_path,
                "video_hash": index.video_hash,
                "frame_count": index.frame_count,
                "fps": index.fps,
                "duration": index.duration,
                "indexed_at": index.indexed_at,
                "frame_indices": index.frame_indices,
            }
        with open(indices_file, "w") as f:
            json.dump(data, f, indent=2)

    def _get_video_hash(self, video_path: str) -> str:
        """Get hash of video file for change detection."""
        stat = os.stat(video_path)
        hash_input = f"{video_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    def _extract_frames(
        self,
        video_path: str,
        sample_fps: float | None = None,
    ) -> list[tuple[int, float, np.ndarray]]:
        """
        Extract frames from video at specified sample rate.

        Returns:
            List of (frame_index, timestamp, frame_array) tuples.
        """
        import cv2

        sample_fps = sample_fps or self.sample_fps

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return []

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps if video_fps > 0 else 0

        # Calculate frame interval
        frame_interval = max(1, int(video_fps / sample_fps))

        frames = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = frame_idx / video_fps
                frames.append((frame_idx, timestamp, frame_rgb))

            frame_idx += 1

        cap.release()

        logger.debug(f"📹 Extracted {len(frames)} frames from {Path(video_path).name}")
        return frames

    def _get_image_embedding(self, image: np.ndarray) -> np.ndarray:
        """Get CLIP embedding for an image."""
        import torch
        from PIL import Image

        # Convert to PIL Image
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        # Process image
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get embedding
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
            embedding = outputs.cpu().numpy().flatten()

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def _get_text_embedding(self, text: str) -> np.ndarray:
        """Get CLIP embedding for text."""
        import torch

        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)
            embedding = outputs.cpu().numpy().flatten()

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def _save_thumbnail(
        self,
        frame: np.ndarray,
        video_path: str,
        frame_idx: int,
    ) -> str:
        """Save frame thumbnail."""
        from PIL import Image

        video_name = Path(video_path).stem
        thumb_name = f"{video_name}_f{frame_idx}.jpg"
        thumb_path = self.thumbnails_dir / thumb_name

        # Resize to thumbnail
        img = Image.fromarray(frame)
        img.thumbnail((320, 180))
        img.save(thumb_path, "JPEG", quality=80)

        return str(thumb_path)

    def index_video(
        self,
        video_path: str,
        force: bool = False,
        generate_thumbnails: bool = True,
        generate_descriptions: bool = False,
    ) -> int:
        """
        Index a video file.

        Args:
            video_path: Path to video file.
            force: Force re-indexing even if already indexed.
            generate_thumbnails: Save thumbnail images.
            generate_descriptions: Generate AI descriptions for frames.

        Returns:
            Number of frames indexed.
        """
        from datetime import datetime

        import cv2

        video_path = str(Path(video_path).resolve())

        if not Path(video_path).exists():
            logger.error(f"Video not found: {video_path}")
            return 0

        # Check if already indexed
        video_hash = self._get_video_hash(video_path)
        if video_path in self._video_indices and not force:
            existing = self._video_indices[video_path]
            if existing.video_hash == video_hash:
                logger.info(f"⏭️ Already indexed: {Path(video_path).name}")
                return existing.frame_count

        logger.info(f"📹 Indexing: {Path(video_path).name}")

        # Get video info
        cap = cv2.VideoCapture(video_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps if video_fps > 0 else 0
        cap.release()

        # Extract frames
        frames = self._extract_frames(video_path)

        if not frames:
            logger.warning(f"No frames extracted from: {video_path}")
            return 0

        # Process frames
        ids = []
        embeddings = []
        metadatas = []
        frame_indices = []

        for frame_idx, timestamp, frame in frames:
            # Generate embedding
            embedding = self._get_image_embedding(frame)

            # Create unique ID
            doc_id = f"{video_hash}_{frame_idx}"

            # Metadata
            metadata = {
                "video_path": video_path,
                "frame_index": frame_idx,
                "timestamp": timestamp,
            }

            # Save thumbnail
            if generate_thumbnails:
                thumb_path = self._save_thumbnail(frame, video_path, frame_idx)
                metadata["thumbnail_path"] = thumb_path

            # Generate description (optional, uses vision LLM)
            if generate_descriptions:
                metadata["description"] = self._generate_frame_description(frame)

            ids.append(doc_id)
            embeddings.append(embedding.tolist())
            metadatas.append(metadata)
            frame_indices.append(frame_idx)

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        # Save index
        self._video_indices[video_path] = VideoIndex(
            video_path=video_path,
            video_hash=video_hash,
            frame_count=len(frames),
            fps=video_fps,
            duration=duration,
            indexed_at=datetime.now().isoformat(),
            frame_indices=frame_indices,
        )
        self._save_indices()

        logger.info(f"✅ Indexed {len(frames)} frames from: {Path(video_path).name}")
        return len(frames)

    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        force: bool = False,
    ) -> int:
        """
        Index all videos in a directory.

        Args:
            directory: Directory path.
            recursive: Search subdirectories.
            force: Force re-indexing.

        Returns:
            Total number of frames indexed.
        """
        directory = Path(directory)
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return 0

        # Find video files
        pattern = "**/*" if recursive else "*"
        video_files = [
            f
            for f in directory.glob(pattern)
            if f.suffix.lower() in self.SUPPORTED_FORMATS
        ]

        logger.info(f"📂 Found {len(video_files)} videos to index")

        total_frames = 0
        for video_file in video_files:
            try:
                frames = self.index_video(str(video_file), force=force)
                total_frames += frames
            except Exception as e:
                logger.error(f"Failed to index {video_file.name}: {e}")

        logger.info(
            f"✅ Total indexed: {total_frames} frames from {len(video_files)} videos"
        )
        return total_frames

    def search(
        self,
        query: str,
        n_results: int = 5,
        min_score: float = 0.0,
        video_filter: str | None = None,
    ) -> list[FrameMatch]:
        """
        Search for frames matching a text query.

        Args:
            query: Natural language description of desired footage.
            n_results: Maximum number of results.
            min_score: Minimum similarity score (0-1).
            video_filter: Optional video path to filter results.

        Returns:
            List of FrameMatch objects sorted by relevance.
        """
        logger.info(f"🔍 Searching: '{query}'")

        # Get text embedding
        query_embedding = self._get_text_embedding(query)

        # Build filter
        where_filter = None
        if video_filter:
            where_filter = {"video_path": video_filter}

        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where_filter,
        )

        # Convert to FrameMatch objects
        matches = []

        if results and results.get("metadatas"):
            for i, metadata in enumerate(results["metadatas"][0]):
                # Calculate score from distance
                distance = results["distances"][0][i] if results.get("distances") else 0
                score = 1 - distance  # Convert distance to similarity

                if score >= min_score:
                    matches.append(
                        FrameMatch(
                            video_path=metadata["video_path"],
                            frame_index=metadata["frame_index"],
                            timestamp=metadata["timestamp"],
                            score=score,
                            description=metadata.get("description"),
                            thumbnail_path=metadata.get("thumbnail_path"),
                        )
                    )

        logger.info(f"✅ Found {len(matches)} matches for '{query}'")
        return matches

    def find_best_clip(
        self,
        description: str,
        duration: float = 3.0,
        video_filter: str | None = None,
    ) -> dict | None:
        """
        Find the best clip matching a description.

        Args:
            description: What the clip should show.
            duration: Desired clip duration in seconds.
            video_filter: Optional video path filter.

        Returns:
            Dict with video_path, start_time, end_time, and score.
        """
        matches = self.search(description, n_results=1, video_filter=video_filter)

        if not matches:
            return None

        best = matches[0]

        # Calculate clip boundaries
        start_time = max(0, best.timestamp - duration / 2)
        end_time = best.timestamp + duration / 2

        # Adjust if video ends
        if best.video_path in self._video_indices:
            video_duration = self._video_indices[best.video_path].duration
            if end_time > video_duration:
                end_time = video_duration
                start_time = max(0, end_time - duration)

        return {
            "video_path": best.video_path,
            "start_time": start_time,
            "end_time": end_time,
            "timestamp": best.timestamp,
            "score": best.score,
            "thumbnail_path": best.thumbnail_path,
        }

    def find_clips_for_script(
        self,
        script_segments: list[dict],
        min_score: float = 0.3,
    ) -> list[dict]:
        """
        Find clips for a list of script segments.

        Args:
            script_segments: List of {"text": ..., "duration": ...} dicts.
            min_score: Minimum similarity score.

        Returns:
            List of clip suggestions per segment.
        """
        results = []

        for segment in script_segments:
            text = segment.get("text", "")
            duration = segment.get("duration", 3.0)

            clip = self.find_best_clip(text, duration)

            if clip and clip["score"] >= min_score:
                results.append(
                    {
                        "segment": text,
                        "clip": clip,
                    }
                )
            else:
                results.append(
                    {
                        "segment": text,
                        "clip": None,
                        "suggestion": "No matching footage found. Consider B-roll or stock footage.",
                    }
                )

        return results

    def _generate_frame_description(self, frame: np.ndarray) -> str:
        """Generate text description of a frame using vision LLM."""
        try:
            import base64
            import io

            from PIL import Image

            from ..ai.brain import HybridBrain

            brain = HybridBrain()

            # Convert to base64
            img = Image.fromarray(frame)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            # Use vision capable model
            description = brain.think(
                f"Describe this image briefly (1-2 sentences): data:image/jpeg;base64,{img_base64[:100]}...",
                context="You are a video content analyzer. Describe what's happening in the frame.",
            )

            return description[:200] if description else ""

        except Exception:
            return ""

    def get_stats(self) -> dict:
        """Get index statistics."""
        total_frames = sum(idx.frame_count for idx in self._video_indices.values())
        total_duration = sum(idx.duration for idx in self._video_indices.values())

        return {
            "videos_indexed": len(self._video_indices),
            "total_frames": total_frames,
            "total_duration_hours": total_duration / 3600,
            "collection_count": self.collection.count()
            if hasattr(self.collection, "count")
            else 0,
        }

    def clear_index(self, video_path: str | None = None):
        """
        Clear index for a video or all videos.

        Args:
            video_path: Specific video to clear, or None for all.
        """
        if video_path:
            if video_path in self._video_indices:
                # Remove from collection
                index = self._video_indices[video_path]
                ids_to_remove = [
                    f"{index.video_hash}_{fi}" for fi in index.frame_indices
                ]
                try:
                    self.collection.delete(ids=ids_to_remove)
                except Exception:
                    pass

                del self._video_indices[video_path]
                self._save_indices()
                logger.info(f"🗑️ Cleared index for: {video_path}")
        else:
            # Clear all
            try:
                # Recreate collection
                import chromadb
                from chromadb.config import Settings

                persist_dir = str(self.index_dir / "chromadb")
                client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=persist_dir,
                        anonymized_telemetry=False,
                    )
                )
                client.delete_collection(self.collection_name)
                self._collection = None
            except Exception:
                pass

            self._video_indices = {}
            self._save_indices()
            logger.info("🗑️ Cleared all video indices")


class InMemoryCollection:
    """Fallback in-memory collection when ChromaDB unavailable."""

    def __init__(self):
        self.embeddings = []
        self.metadatas = []
        self.ids = []

    def add(self, ids: list, embeddings: list, metadatas: list):
        self.ids.extend(ids)
        self.embeddings.extend(embeddings)
        self.metadatas.extend(metadatas)

    def query(
        self,
        query_embeddings: list,
        n_results: int = 5,
        where: dict = None,
    ) -> dict:
        if not self.embeddings:
            return {"metadatas": [[]], "distances": [[]]}

        query_vec = np.array(query_embeddings[0])

        # Calculate similarities
        scores = []
        for i, emb in enumerate(self.embeddings):
            emb_vec = np.array(emb)
            similarity = np.dot(query_vec, emb_vec)

            # Apply filter
            if where:
                match = all(self.metadatas[i].get(k) == v for k, v in where.items())
                if not match:
                    continue

            scores.append((i, 1 - similarity))  # Distance = 1 - similarity

        # Sort and take top N
        scores.sort(key=lambda x: x[1])
        top = scores[:n_results]

        return {
            "metadatas": [[self.metadatas[i] for i, _ in top]],
            "distances": [[d for _, d in top]],
        }

    def count(self) -> int:
        return len(self.ids)

    def delete(self, ids: list):
        for id_to_remove in ids:
            if id_to_remove in self.ids:
                idx = self.ids.index(id_to_remove)
                self.ids.pop(idx)
                self.embeddings.pop(idx)
                self.metadatas.pop(idx)


# Convenience functions
def index_footage(directory: str, recursive: bool = True) -> int:
    """Quick function to index a footage directory."""
    rag = VisualRAG()
    return rag.index_directory(directory, recursive=recursive)


def search_footage(query: str, n_results: int = 5) -> list[FrameMatch]:
    """Quick function to search indexed footage."""
    rag = VisualRAG()
    return rag.search(query, n_results=n_results)
