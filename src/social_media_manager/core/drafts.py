"""
Draft Auto-Save and Recovery System for AgencyOS.

Features:
- Automatic saving of work-in-progress content
- Recovery from crashes or accidental closes
- Version history with rollback
- Cross-session persistence
"""

import json
import shutil
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from ..config import config


@dataclass
class Draft:
    """A saved draft of content in progress."""

    id: str
    type: Literal["video", "caption", "campaign", "post", "script"]
    title: str
    content: dict[str, Any]

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    auto_saved: bool = False
    version: int = 1

    # Recovery info
    session_id: str | None = None
    was_recovered: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "auto_saved": self.auto_saved,
            "version": self.version,
            "session_id": self.session_id,
            "was_recovered": self.was_recovered,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Draft":
        return cls(**data)


class DraftManager:
    """
    Manage content drafts with auto-save and recovery.

    Example:
        drafts = DraftManager()

        # Create a new draft
        draft = drafts.create_draft(
            type="video",
            title="My Awesome Video",
            content={
                "script": "Hook: ...",
                "music": "upbeat",
                "clips": ["clip1.mp4", "clip2.mp4"],
            }
        )

        # Auto-save updates
        drafts.auto_save(draft.id, {
            "script": "Updated script...",
            "progress": 50,
        })

        # Recover after crash
        recovered = drafts.get_recoverable_drafts()
        for draft in recovered:
            print(f"Recovered: {draft.title}")

        # Get version history
        versions = drafts.get_versions(draft.id)
    """

    # Auto-save interval in seconds
    AUTO_SAVE_INTERVAL = 30

    # Maximum versions to keep per draft
    MAX_VERSIONS = 10

    # Days to keep old drafts
    RETENTION_DAYS = 30

    def __init__(self, drafts_dir: Path | None = None):
        self.drafts_dir = drafts_dir or (config.BASE_DIR / "drafts")
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

        self.versions_dir = self.drafts_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        self._drafts: dict[str, Draft] = {}
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self._load_drafts()
        self._cleanup_old_drafts()

        logger.info(f"📝 Draft Manager initialized (session: {self._session_id})")

    def _load_drafts(self):
        """Load drafts from disk."""
        drafts_file = self.drafts_dir / "drafts.json"
        if drafts_file.exists():
            try:
                with open(drafts_file) as f:
                    data = json.load(f)
                    for draft_data in data:
                        draft = Draft.from_dict(draft_data)
                        self._drafts[draft.id] = draft
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse drafts.json: {e}")
            except KeyError as e:
                logger.warning(f"Invalid draft data (missing key): {e}")
            except OSError as e:
                logger.warning(f"Failed to load drafts (I/O error): {e}")
            except Exception as e:
                logger.warning(f"Failed to load drafts ({type(e).__name__}): {e}")
                logger.debug(traceback.format_exc())

    def _save_drafts(self):
        """Save drafts to disk."""
        drafts_file = self.drafts_dir / "drafts.json"
        try:
            data = [d.to_dict() for d in self._drafts.values()]
            with open(drafts_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.warning(f"Failed to save drafts (I/O error): {e}")
        except Exception as e:
            logger.warning(f"Failed to save drafts ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())

    def _cleanup_old_drafts(self):
        """Remove drafts older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.RETENTION_DAYS)

        to_delete = []
        for draft_id, draft in self._drafts.items():
            updated = datetime.fromisoformat(draft.updated_at)
            if updated < cutoff:
                to_delete.append(draft_id)

        for draft_id in to_delete:
            self.delete_draft(draft_id, permanent=True)

        if to_delete:
            logger.info(f"🗑️ Cleaned up {len(to_delete)} old drafts")

    def _save_version(self, draft: Draft):
        """Save a version snapshot of a draft."""
        version_dir = self.versions_dir / draft.id
        version_dir.mkdir(parents=True, exist_ok=True)

        # Save version
        version_file = version_dir / f"v{draft.version}.json"
        with open(version_file, "w") as f:
            json.dump(draft.to_dict(), f, indent=2)

        # Cleanup old versions
        versions = sorted(version_dir.glob("v*.json"))
        while len(versions) > self.MAX_VERSIONS:
            versions[0].unlink()
            versions = versions[1:]

    def create_draft(
        self,
        type: Literal["video", "caption", "campaign", "post", "script"],
        title: str,
        content: dict[str, Any],
    ) -> Draft:
        """
        Create a new draft.

        Args:
            type: Draft type.
            title: Draft title.
            content: Draft content as dict.

        Returns:
            Created Draft.
        """
        import hashlib

        draft_id = hashlib.md5(
            f"{title}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        draft = Draft(
            id=draft_id,
            type=type,
            title=title,
            content=content,
            session_id=self._session_id,
        )

        self._drafts[draft_id] = draft
        self._save_drafts()
        self._save_version(draft)

        logger.info(f"📝 Created draft: {title} ({draft_id})")
        return draft

    def get_draft(self, draft_id: str) -> Draft | None:
        """Get a draft by ID."""
        return self._drafts.get(draft_id)

    def update_draft(
        self,
        draft_id: str,
        content: dict[str, Any] | None = None,
        title: str | None = None,
        save_version: bool = True,
    ) -> Draft | None:
        """
        Update a draft.

        Args:
            draft_id: Draft ID.
            content: Updated content (merged with existing).
            title: Updated title.
            save_version: Whether to save a version snapshot.

        Returns:
            Updated Draft.
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            return None

        if title:
            draft.title = title

        if content:
            draft.content.update(content)

        draft.updated_at = datetime.now().isoformat()
        draft.version += 1
        draft.session_id = self._session_id
        draft.auto_saved = False

        self._save_drafts()

        if save_version:
            self._save_version(draft)

        return draft

    def auto_save(
        self,
        draft_id: str,
        content: dict[str, Any],
    ) -> Draft | None:
        """
        Auto-save draft content (no version snapshot).

        Args:
            draft_id: Draft ID.
            content: Content to merge.

        Returns:
            Updated Draft.
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            return None

        draft.content.update(content)
        draft.updated_at = datetime.now().isoformat()
        draft.session_id = self._session_id
        draft.auto_saved = True

        self._save_drafts()

        logger.debug(f"💾 Auto-saved draft: {draft.title}")
        return draft

    def delete_draft(
        self,
        draft_id: str,
        permanent: bool = False,
    ) -> bool:
        """
        Delete a draft.

        Args:
            draft_id: Draft ID.
            permanent: Also delete version history.

        Returns:
            True if deleted.
        """
        if draft_id not in self._drafts:
            return False

        del self._drafts[draft_id]
        self._save_drafts()

        if permanent:
            version_dir = self.versions_dir / draft_id
            if version_dir.exists():
                shutil.rmtree(version_dir)

        logger.info(f"🗑️ Deleted draft: {draft_id}")
        return True

    def list_drafts(
        self,
        type: str | None = None,
        search: str | None = None,
    ) -> list[Draft]:
        """
        List drafts with optional filtering.

        Args:
            type: Filter by draft type.
            search: Search in title.

        Returns:
            List of drafts sorted by updated_at.
        """
        drafts = list(self._drafts.values())

        if type:
            drafts = [d for d in drafts if d.type == type]

        if search:
            search_lower = search.lower()
            drafts = [d for d in drafts if search_lower in d.title.lower()]

        # Sort by most recently updated
        drafts.sort(key=lambda d: d.updated_at, reverse=True)

        return drafts

    def get_recoverable_drafts(self) -> list[Draft]:
        """
        Get drafts that were auto-saved in a previous session.
        These are candidates for recovery after a crash.

        Returns:
            List of recoverable drafts.
        """
        recoverable = []

        for draft in self._drafts.values():
            # Draft from a different session that was auto-saved
            if draft.session_id != self._session_id and draft.auto_saved:
                draft.was_recovered = True
                recoverable.append(draft)

        return recoverable

    def get_versions(self, draft_id: str) -> list[dict]:
        """
        Get version history for a draft.

        Args:
            draft_id: Draft ID.

        Returns:
            List of version dicts with metadata.
        """
        version_dir = self.versions_dir / draft_id
        if not version_dir.exists():
            return []

        versions = []
        for version_file in sorted(version_dir.glob("v*.json"), reverse=True):
            try:
                with open(version_file) as f:
                    data = json.load(f)
                    versions.append(
                        {
                            "version": data.get("version", 0),
                            "updated_at": data.get("updated_at"),
                            "file": str(version_file),
                        }
                    )
            except Exception:
                continue

        return versions

    def restore_version(
        self,
        draft_id: str,
        version: int,
    ) -> Draft | None:
        """
        Restore a draft to a previous version.

        Args:
            draft_id: Draft ID.
            version: Version number to restore.

        Returns:
            Restored Draft.
        """
        version_file = self.versions_dir / draft_id / f"v{version}.json"
        if not version_file.exists():
            return None

        try:
            with open(version_file) as f:
                data = json.load(f)

            # Create new version based on old
            draft = self._drafts.get(draft_id)
            if draft:
                draft.content = data.get("content", {})
                draft.title = data.get("title", draft.title)
                draft.updated_at = datetime.now().isoformat()
                draft.version += 1
                draft.auto_saved = False

                self._save_drafts()
                self._save_version(draft)

                logger.info(f"🔄 Restored draft to version {version}: {draft.title}")
                return draft

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse version file: {e}")
        except KeyError as e:
            logger.error(f"Invalid version data (missing key): {e}")
        except OSError as e:
            logger.error(f"Failed to restore version (I/O error): {e}")
        except Exception as e:
            logger.error(f"Failed to restore version ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())

        return None

    def export_draft(self, draft_id: str) -> dict | None:
        """Export a draft as a standalone file."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None

        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "draft": draft.to_dict(),
        }

    def import_draft(self, data: dict) -> Draft | None:
        """Import a draft from exported data."""
        try:
            draft_data = data.get("draft", {})

            # Generate new ID to avoid conflicts
            import hashlib

            new_id = hashlib.md5(
                f"{draft_data.get('title', 'import')}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]

            draft_data["id"] = new_id
            draft_data["created_at"] = datetime.now().isoformat()
            draft_data["updated_at"] = datetime.now().isoformat()
            draft_data["session_id"] = self._session_id
            draft_data["version"] = 1

            draft = Draft.from_dict(draft_data)
            self._drafts[draft.id] = draft
            self._save_drafts()

            logger.info(f"📥 Imported draft: {draft.title}")
            return draft

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse import data: {e}")
            return None
        except KeyError as e:
            logger.error(f"Invalid import data (missing key): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to import draft ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return None


# Singleton instance
_draft_manager: DraftManager | None = None


def get_draft_manager() -> DraftManager:
    """Get the global draft manager."""
    global _draft_manager
    if _draft_manager is None:
        _draft_manager = DraftManager()
    return _draft_manager


def auto_save_draft(draft_id: str, content: dict) -> Draft | None:
    """Quick function to auto-save a draft."""
    return get_draft_manager().auto_save(draft_id, content)


def recover_drafts() -> list[Draft]:
    """Quick function to get recoverable drafts."""
    return get_draft_manager().get_recoverable_drafts()
