"""
Project Configuration Export/Import for AgencyOS.

Export and import complete project configurations including:
- Client settings
- Templates
- Drafts
- Scheduled posts
- API configurations (sanitized)
"""

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from ..config import config


@dataclass
class ExportManifest:
    """Manifest describing an export package."""

    version: str = "1.0"
    app_version: str = "2.4"
    created_at: str = ""
    includes: dict[str, bool] = None
    stats: dict[str, int] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.includes is None:
            self.includes = {}
        if self.stats is None:
            self.stats = {}


class ProjectExporter:
    """
    Export and import AgencyOS project configurations.

    Example:
        exporter = ProjectExporter()

        # Export everything
        path = exporter.export_all("my_backup.zip")

        # Export specific components
        path = exporter.export(
            output_path="partial_backup.zip",
            include_templates=True,
            include_drafts=True,
            include_clients=False,
        )

        # Import from backup
        stats = exporter.import_backup("my_backup.zip")
        print(f"Imported {stats['templates']} templates")
    """

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or config.BASE_DIR
        self.exports_dir = self.base_dir / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        output_path: str | Path | None = None,
        include_templates: bool = True,
        include_drafts: bool = True,
        include_clients: bool = True,
        include_schedules: bool = True,
        include_api_config: bool = False,  # Sensitive!
        include_assets: bool = False,  # Can be large
    ) -> Path:
        """
        Export project configuration to a ZIP file.

        Args:
            output_path: Output file path (auto-generated if None).
            include_templates: Include content templates.
            include_drafts: Include saved drafts.
            include_clients: Include client configurations.
            include_schedules: Include scheduled posts.
            include_api_config: Include API keys (use with caution!).
            include_assets: Include media assets (can be large).

        Returns:
            Path to the created export file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if output_path is None:
            output_path = self.exports_dir / f"agencyos_export_{timestamp}.zip"
        else:
            output_path = Path(output_path)

        # Create manifest
        manifest = ExportManifest(
            includes={
                "templates": include_templates,
                "drafts": include_drafts,
                "clients": include_clients,
                "schedules": include_schedules,
                "api_config": include_api_config,
                "assets": include_assets,
            }
        )

        # Collect data
        export_data: dict[str, Any] = {}

        if include_templates:
            templates = self._export_templates()
            export_data["templates"] = templates
            manifest.stats["templates"] = len(templates)

        if include_drafts:
            drafts = self._export_drafts()
            export_data["drafts"] = drafts
            manifest.stats["drafts"] = len(drafts)

        if include_clients:
            clients = self._export_clients()
            export_data["clients"] = clients
            manifest.stats["clients"] = len(clients)

        if include_schedules:
            schedules = self._export_schedules()
            export_data["schedules"] = schedules
            manifest.stats["schedules"] = len(schedules)

        if include_api_config:
            logger.warning("⚠️ Including API config - keep this file secure!")
            export_data["api_config"] = self._export_api_config()

        # Create ZIP file
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            zf.writestr("manifest.json", json.dumps(manifest.__dict__, indent=2))

            # Add export data
            zf.writestr("data.json", json.dumps(export_data, indent=2))

            # Add assets if requested
            if include_assets:
                self._add_assets_to_zip(zf)

        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"📦 Export created: {output_path.name} ({size_mb:.2f}MB)")

        return output_path

    def export_all(self, output_path: str | Path | None = None) -> Path:
        """Export everything (except API keys and assets)."""
        return self.export(
            output_path=output_path,
            include_templates=True,
            include_drafts=True,
            include_clients=True,
            include_schedules=True,
            include_api_config=False,
            include_assets=False,
        )

    def import_backup(
        self,
        backup_path: str | Path,
        overwrite: bool = False,
        restore_templates: bool = True,
        restore_drafts: bool = True,
        restore_clients: bool = True,
        restore_schedules: bool = True,
    ) -> dict[str, int]:
        """
        Import from a backup file.

        Args:
            backup_path: Path to the backup ZIP file.
            overwrite: Whether to overwrite existing items.
            restore_templates: Restore templates.
            restore_drafts: Restore drafts.
            restore_clients: Restore client configurations.
            restore_schedules: Restore scheduled posts.

        Returns:
            Dict with counts of items restored per category.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        stats = {
            "templates": 0,
            "drafts": 0,
            "clients": 0,
            "schedules": 0,
        }

        with zipfile.ZipFile(backup_path, "r") as zf:
            # Read manifest
            try:
                manifest_data = json.loads(zf.read("manifest.json"))
                logger.info(
                    f"📦 Importing backup from {manifest_data.get('created_at', 'unknown')}"
                )
            except Exception:
                logger.warning("No manifest found, assuming full backup")

            # Read data
            try:
                data = json.loads(zf.read("data.json"))
            except Exception as e:
                raise ValueError(f"Invalid backup file: {e}")

            # Restore components
            if restore_templates and "templates" in data:
                stats["templates"] = self._import_templates(
                    data["templates"], overwrite
                )

            if restore_drafts and "drafts" in data:
                stats["drafts"] = self._import_drafts(data["drafts"], overwrite)

            if restore_clients and "clients" in data:
                stats["clients"] = self._import_clients(data["clients"], overwrite)

            if restore_schedules and "schedules" in data:
                stats["schedules"] = self._import_schedules(
                    data["schedules"], overwrite
                )

        logger.info(f"✅ Import complete: {sum(stats.values())} items restored")
        return stats

    def _export_templates(self) -> list[dict]:
        """Export templates."""
        templates_file = self.base_dir / "templates" / "templates.json"
        if templates_file.exists():
            try:
                with open(templates_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _export_drafts(self) -> list[dict]:
        """Export drafts."""
        drafts_file = self.base_dir / "drafts" / "drafts.json"
        if drafts_file.exists():
            try:
                with open(drafts_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _export_clients(self) -> dict:
        """Export client configurations."""
        clients_file = self.base_dir / "clients" / "clients.yaml"
        if clients_file.exists():
            try:
                import yaml

                with open(clients_file) as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def _export_schedules(self) -> list[dict]:
        """Export scheduled posts."""
        # This would integrate with your scheduling system
        schedules_file = self.base_dir / "schedules" / "scheduled_posts.json"
        if schedules_file.exists():
            try:
                with open(schedules_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _export_api_config(self) -> dict:
        """Export sanitized API configuration."""
        # Only export non-sensitive config
        return {
            "ollama_url": config.OLLAMA_URL,
            "ollama_model": config.OLLAMA_MODEL,
            "llm_provider": config.LLM_PROVIDER,
            "llm_model": config.LLM_MODEL,
            # Don't include actual API keys!
            "apis_configured": {
                "groq": bool(config.GROQ_API_KEY),
                "gemini": bool(config.GEMINI_API_KEY),
                "openai": bool(config.OPENAI_API_KEY),
                "pexels": bool(config.PEXELS_API_KEY),
                "pixabay": bool(config.PIXABAY_API_KEY),
            },
        }

    def _add_assets_to_zip(self, zf: zipfile.ZipFile):
        """Add media assets to ZIP (only essential ones)."""
        # Add fonts
        fonts_dir = self.base_dir / "assets" / "fonts"
        if fonts_dir.exists():
            for font_file in fonts_dir.glob("*.ttf"):
                zf.write(font_file, f"assets/fonts/{font_file.name}")

        # Add overlays
        overlays_dir = self.base_dir / "assets" / "overlays"
        if overlays_dir.exists():
            for overlay in overlays_dir.glob("*.png"):
                zf.write(overlay, f"assets/overlays/{overlay.name}")

    def _import_templates(self, templates: list[dict], overwrite: bool) -> int:
        """Import templates."""
        templates_dir = self.base_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        existing_file = templates_dir / "templates.json"
        existing = []
        if existing_file.exists() and not overwrite:
            try:
                with open(existing_file) as f:
                    existing = json.load(f)
            except Exception:
                pass

        # Merge or replace
        if overwrite:
            merged = templates
        else:
            existing_ids = {t.get("id") for t in existing}
            new_templates = [t for t in templates if t.get("id") not in existing_ids]
            merged = existing + new_templates

        with open(existing_file, "w") as f:
            json.dump(merged, f, indent=2)

        return len(templates)

    def _import_drafts(self, drafts: list[dict], overwrite: bool) -> int:
        """Import drafts."""
        drafts_dir = self.base_dir / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        existing_file = drafts_dir / "drafts.json"
        existing = []
        if existing_file.exists() and not overwrite:
            try:
                with open(existing_file) as f:
                    existing = json.load(f)
            except Exception:
                pass

        if overwrite:
            merged = drafts
        else:
            existing_ids = {d.get("id") for d in existing}
            new_drafts = [d for d in drafts if d.get("id") not in existing_ids]
            merged = existing + new_drafts

        with open(existing_file, "w") as f:
            json.dump(merged, f, indent=2)

        return len(drafts)

    def _import_clients(self, clients: dict, overwrite: bool) -> int:
        """Import client configurations."""
        clients_dir = self.base_dir / "clients"
        clients_dir.mkdir(parents=True, exist_ok=True)

        clients_file = clients_dir / "clients.yaml"

        try:
            import yaml

            existing = {}
            if clients_file.exists() and not overwrite:
                with open(clients_file) as f:
                    existing = yaml.safe_load(f) or {}

            if overwrite:
                merged = clients
            else:
                merged = {**existing, **clients}

            with open(clients_file, "w") as f:
                yaml.dump(merged, f, default_flow_style=False)

            return len(clients)

        except ImportError:
            logger.warning("PyYAML not installed, skipping client import")
            return 0

    def _import_schedules(self, schedules: list[dict], overwrite: bool) -> int:
        """Import scheduled posts."""
        schedules_dir = self.base_dir / "schedules"
        schedules_dir.mkdir(parents=True, exist_ok=True)

        schedules_file = schedules_dir / "scheduled_posts.json"

        existing = []
        if schedules_file.exists() and not overwrite:
            try:
                with open(schedules_file) as f:
                    existing = json.load(f)
            except Exception:
                pass

        if overwrite:
            merged = schedules
        else:
            existing_ids = {s.get("id") for s in existing}
            new_schedules = [s for s in schedules if s.get("id") not in existing_ids]
            merged = existing + new_schedules

        with open(schedules_file, "w") as f:
            json.dump(merged, f, indent=2)

        return len(schedules)

    def list_backups(self) -> list[dict]:
        """List available backup files."""
        backups = []

        for backup_file in self.exports_dir.glob("*.zip"):
            try:
                with zipfile.ZipFile(backup_file, "r") as zf:
                    manifest = json.loads(zf.read("manifest.json"))
                    backups.append(
                        {
                            "path": str(backup_file),
                            "name": backup_file.name,
                            "created_at": manifest.get("created_at"),
                            "size_mb": backup_file.stat().st_size / (1024 * 1024),
                            "stats": manifest.get("stats", {}),
                        }
                    )
            except Exception:
                backups.append(
                    {
                        "path": str(backup_file),
                        "name": backup_file.name,
                        "created_at": None,
                        "size_mb": backup_file.stat().st_size / (1024 * 1024),
                        "stats": {},
                    }
                )

        # Sort by creation date
        backups.sort(key=lambda b: b.get("created_at") or "", reverse=True)

        return backups

    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup file."""
        backup_path = self.exports_dir / backup_name
        if backup_path.exists():
            backup_path.unlink()
            logger.info(f"🗑️ Deleted backup: {backup_name}")
            return True
        return False


# Convenience functions
def export_project(output_path: str | None = None) -> Path:
    """Quick function to export project."""
    return ProjectExporter().export_all(output_path)


def import_project(backup_path: str, overwrite: bool = False) -> dict:
    """Quick function to import project."""
    return ProjectExporter().import_backup(backup_path, overwrite=overwrite)
