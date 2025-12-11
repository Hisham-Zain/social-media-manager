"""
Project State Management for Resumable Video Production.

Implements checkpoint-based state persistence that allows video production
to resume from the last successful step after interruption.

Features:
- JSON-backed manifest for state persistence
- Asset validation and checksumming
- Step-by-step progress tracking
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger


class ProductionStep(str, Enum):
    """Enumeration of production pipeline steps."""

    VOICEOVER = "voiceover"
    AVATAR = "avatar"
    MUSIC = "music"
    COMPOSITION = "composition"
    THUMBNAIL = "thumbnail"
    UPLOAD = "upload"


class AssetStatus(str, Enum):
    """Status of a production asset."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AssetInfo:
    """Information about a production asset."""

    asset_type: str
    path: str | None = None
    status: AssetStatus = AssetStatus.PENDING
    checksum: str | None = None
    created_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_type": self.asset_type,
            "path": self.path,
            "status": self.status.value,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetInfo":
        return cls(
            asset_type=data["asset_type"],
            path=data.get("path"),
            status=AssetStatus(data.get("status", "pending")),
            checksum=data.get("checksum"),
            created_at=data.get("created_at"),
            error=data.get("error"),
        )


@dataclass
class ProductionState:
    """
    Tracks completion state of each production step.

    Used to determine where to resume after interruption.
    """

    project_name: str
    project_dir: Path
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Asset tracking
    assets: dict[str, AssetInfo] = field(default_factory=dict)

    # Configuration snapshot
    config_snapshot: dict[str, Any] = field(default_factory=dict)

    # Progress tracking
    current_step: ProductionStep | None = None
    completed_steps: list[str] = field(default_factory=list)

    def mark_step_complete(self, step: ProductionStep) -> None:
        """Mark a step as completed."""
        if step.value not in self.completed_steps:
            self.completed_steps.append(step.value)
        self.updated_at = datetime.now().isoformat()

    def is_step_complete(self, step: ProductionStep) -> bool:
        """Check if a step is completed."""
        return step.value in self.completed_steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_dir": str(self.project_dir),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "assets": {k: v.to_dict() for k, v in self.assets.items()},
            "config_snapshot": self.config_snapshot,
            "current_step": self.current_step.value if self.current_step else None,
            "completed_steps": self.completed_steps,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductionState":
        state = cls(
            project_name=data["project_name"],
            project_dir=Path(data["project_dir"]),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
        state.assets = {
            k: AssetInfo.from_dict(v) for k, v in data.get("assets", {}).items()
        }
        state.config_snapshot = data.get("config_snapshot", {})
        state.current_step = (
            ProductionStep(data["current_step"]) if data.get("current_step") else None
        )
        state.completed_steps = data.get("completed_steps", [])
        return state


class ProjectManifest:
    """
    JSON-backed state persistence for VideoProject.

    Manages the manifest.json file that tracks production progress,
    enabling resumption after crashes or interruptions.

    Example:
        manifest = ProjectManifest(project_dir)

        # Check if asset exists
        if manifest.has_asset("audio"):
            audio_path = manifest.get_asset_path("audio")
        else:
            audio_path = generate_audio(...)
            manifest.register_asset("audio", audio_path)
            manifest.save()
    """

    MANIFEST_FILENAME = "manifest.json"

    def __init__(self, project_dir: Path | str, project_name: str = "Untitled"):
        """
        Initialize manifest for a project directory.

        Args:
            project_dir: Directory where project assets are stored.
            project_name: Human-readable project name.
        """
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.project_dir / self.MANIFEST_FILENAME

        # Load or create state
        if self.manifest_path.exists():
            self.state = self._load()
            logger.info(f"📂 Loaded manifest: {project_name}")
        else:
            self.state = ProductionState(
                project_name=project_name,
                project_dir=self.project_dir,
            )
            logger.info(f"📝 Created new manifest: {project_name}")

    def _load(self) -> ProductionState:
        """Load state from manifest file."""
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProductionState.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"⚠️ Manifest corrupted, creating new: {e}")
            return ProductionState(
                project_name="Recovered",
                project_dir=self.project_dir,
            )

    def save(self) -> None:
        """Save state to manifest file."""
        self.state.updated_at = datetime.now().isoformat()
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2)
            logger.debug(f"💾 Manifest saved: {self.manifest_path}")
        except OSError as e:
            logger.error(f"Failed to save manifest: {e}")

    def has_asset(self, asset_type: str, validate: bool = True) -> bool:
        """
        Check if an asset exists and is valid.

        Args:
            asset_type: Type of asset (audio, avatar_video, music, etc.)
            validate: If True, verify the file exists on disk.

        Returns:
            True if asset is complete and (optionally) exists on disk.
        """
        if asset_type not in self.state.assets:
            return False

        asset = self.state.assets[asset_type]

        if asset.status != AssetStatus.COMPLETE:
            return False

        if validate and asset.path:
            if not Path(asset.path).exists():
                logger.warning(f"⚠️ Asset file missing: {asset.path}")
                return False

        return True

    def get_asset_path(self, asset_type: str) -> str | None:
        """Get the path to a registered asset."""
        if asset_type in self.state.assets:
            return self.state.assets[asset_type].path
        return None

    def get_asset(self, asset_type: str) -> AssetInfo | None:
        """Get full asset information."""
        return self.state.assets.get(asset_type)

    def register_asset(
        self,
        asset_type: str,
        path: str,
        status: AssetStatus = AssetStatus.COMPLETE,
        compute_checksum: bool = True,
    ) -> None:
        """
        Register an asset in the manifest.

        Args:
            asset_type: Type of asset.
            path: Path to the asset file.
            status: Current status of the asset.
            compute_checksum: Whether to compute file checksum.
        """
        checksum = None
        if compute_checksum and Path(path).exists():
            checksum = self._compute_checksum(path)

        self.state.assets[asset_type] = AssetInfo(
            asset_type=asset_type,
            path=path,
            status=status,
            checksum=checksum,
            created_at=datetime.now().isoformat(),
        )

        logger.debug(f"✅ Registered asset: {asset_type} -> {path}")

    def mark_asset_failed(self, asset_type: str, error: str) -> None:
        """Mark an asset as failed with error message."""
        if asset_type in self.state.assets:
            self.state.assets[asset_type].status = AssetStatus.FAILED
            self.state.assets[asset_type].error = error
        else:
            self.state.assets[asset_type] = AssetInfo(
                asset_type=asset_type,
                status=AssetStatus.FAILED,
                error=error,
            )

    def mark_step_complete(self, step: ProductionStep) -> None:
        """Mark a production step as complete."""
        self.state.mark_step_complete(step)
        self.save()

    def is_step_complete(self, step: ProductionStep) -> bool:
        """Check if a production step is complete."""
        return self.state.is_step_complete(step)

    def set_current_step(self, step: ProductionStep) -> None:
        """Set the currently executing step."""
        self.state.current_step = step
        self.save()

    def save_config(self, config: dict[str, Any]) -> None:
        """Save configuration snapshot for validation on resume."""
        self.state.config_snapshot = config
        self.save()

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Check if current config matches saved config."""
        if not self.state.config_snapshot:
            return True  # No saved config, accept any

        # Check critical fields
        critical_keys = ["script", "platform", "voice", "avatar_image"]
        for key in critical_keys:
            if self.state.config_snapshot.get(key) != config.get(key):
                logger.warning(f"⚠️ Config mismatch on '{key}', may need fresh start")
                return False

        return True

    def get_resume_point(self) -> ProductionStep | None:
        """
        Determine where to resume production.

        Returns the first incomplete step, or None if all complete.
        """
        step_order = [
            ProductionStep.VOICEOVER,
            ProductionStep.AVATAR,
            ProductionStep.MUSIC,
            ProductionStep.COMPOSITION,
        ]

        for step in step_order:
            if not self.is_step_complete(step):
                return step

        return None

    def reset(self) -> None:
        """Reset manifest to initial state."""
        self.state = ProductionState(
            project_name=self.state.project_name,
            project_dir=self.project_dir,
        )
        self.save()
        logger.info("🔄 Manifest reset")

    def _compute_checksum(self, path: str, block_size: int = 65536) -> str:
        """Compute MD5 checksum of a file."""
        hasher = hashlib.md5()
        try:
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(block_size), b""):
                    hasher.update(block)
            return hasher.hexdigest()[:16]
        except OSError:
            return ""

    def get_stats(self) -> dict[str, Any]:
        """Get manifest statistics."""
        return {
            "project_name": self.state.project_name,
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at,
            "total_assets": len(self.state.assets),
            "completed_steps": len(self.state.completed_steps),
            "current_step": self.state.current_step.value
            if self.state.current_step
            else None,
            "resume_point": self.get_resume_point().value
            if self.get_resume_point()
            else None,
        }
