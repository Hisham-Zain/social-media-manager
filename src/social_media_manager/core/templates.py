"""
Content Templates System for AgencyOS.

Create, manage, and use templates for recurring content types:
- Video templates with preset scripts, music, styles
- Caption templates with placeholders
- Campaign templates with full workflows
"""

import json
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from ..config import config


@dataclass
class ContentTemplate:
    """A reusable content template."""

    id: str
    name: str
    type: Literal["video", "caption", "campaign", "post"]
    description: str = ""

    # Template content
    script_template: str = ""
    caption_template: str = ""
    hashtags: list[str] = field(default_factory=list)

    # Video settings
    music_style: str | None = None
    voice_profile: str | None = None
    visual_style: str | None = None
    duration_target: int = 60  # seconds
    platform: str = "instagram"

    # Metadata
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    use_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "script_template": self.script_template,
            "caption_template": self.caption_template,
            "hashtags": self.hashtags,
            "music_style": self.music_style,
            "voice_profile": self.voice_profile,
            "visual_style": self.visual_style,
            "duration_target": self.duration_target,
            "platform": self.platform,
            "category": self.category,
            "tags": self.tags,
            "use_count": self.use_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContentTemplate":
        return cls(**data)


class TemplateManager:
    """
    Manage content templates for recurring content creation.

    Example:
        manager = TemplateManager()

        # Create a template
        template = manager.create_template(
            name="Product Review Video",
            type="video",
            script_template="Today I'm reviewing {product_name}. {key_points}",
            caption_template="🔥 New review: {product_name}! Link in bio.",
            hashtags=["review", "tech", "unboxing"],
            music_style="upbeat",
            platform="youtube"
        )

        # Use the template
        content = manager.apply_template(
            template.id,
            variables={
                "product_name": "iPhone 15 Pro",
                "key_points": "Camera, performance, battery life."
            }
        )
        print(content["script"])
        print(content["caption"])

        # List templates
        templates = manager.list_templates(type="video")
    """

    BUILTIN_TEMPLATES = [
        {
            "id": "product_review",
            "name": "Product Review",
            "type": "video",
            "description": "Standard product review format",
            "script_template": """Hook: Have you been wondering about {product_name}?

Intro: Today I'm going to share my honest review after using it for {time_period}.

Key Points:
{key_points}

Verdict: {verdict}

Call to Action: {cta}""",
            "caption_template": "🔥 {product_name} Review | {verdict}\n\n{summary}\n\n{cta}",
            "hashtags": ["review", "honest", "tech"],
            "music_style": "corporate",
            "duration_target": 90,
            "category": "reviews",
        },
        {
            "id": "tutorial_howto",
            "name": "How-To Tutorial",
            "type": "video",
            "description": "Step-by-step tutorial format",
            "script_template": """Hook: Want to learn how to {topic}?

In this video, I'll show you exactly how in {num_steps} easy steps.

Step 1: {step_1}
Step 2: {step_2}
Step 3: {step_3}

Pro Tip: {pro_tip}

That's it! Now you know how to {topic}.""",
            "caption_template": "📚 How to {topic} in {num_steps} steps!\n\n{summary}\n\nSave this for later! 📌",
            "hashtags": ["tutorial", "howto", "tips", "learn"],
            "music_style": "inspirational",
            "duration_target": 120,
            "category": "education",
        },
        {
            "id": "daily_motivation",
            "name": "Daily Motivation",
            "type": "caption",
            "description": "Motivational quote post",
            "caption_template": "💪 {quote}\n\n{reflection}\n\nDouble tap if you agree! ❤️",
            "hashtags": ["motivation", "mindset", "success", "inspiration"],
            "category": "motivation",
        },
        {
            "id": "behind_scenes",
            "name": "Behind the Scenes",
            "type": "video",
            "description": "BTS content showing process",
            "script_template": """Ever wonder what goes into {what}?

Let me show you behind the scenes of {context}.

[Show process: {process_description}]

The best part? {best_part}

Follow for more BTS content!""",
            "caption_template": "🎬 Behind the scenes of {what}\n\n{description}\n\nComment if you want to see more! 👇",
            "hashtags": ["bts", "behindthescenes", "process", "creator"],
            "music_style": "chill",
            "duration_target": 45,
            "category": "lifestyle",
        },
        {
            "id": "product_launch",
            "name": "Product Launch",
            "type": "campaign",
            "description": "Full product launch campaign",
            "script_template": """TEASER (Day -3):
Something exciting is coming... {hint}

REVEAL (Day 0):
Introducing {product_name}! {tagline}

{key_features}

Available now at {link}

FOLLOW-UP (Day +3):
{product_name} is already {social_proof}!

Don't miss out - {urgency}""",
            "caption_template": "🚀 {product_name} is HERE!\n\n{key_benefit}\n\n🔗 {link}\n\n{cta}",
            "hashtags": ["launch", "new", "announcement"],
            "category": "marketing",
        },
    ]

    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = templates_dir or (config.BASE_DIR / "templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        self._templates: dict[str, ContentTemplate] = {}
        self._load_templates()
        self._ensure_builtins()

        logger.info(
            f"📄 Template Manager initialized ({len(self._templates)} templates)"
        )

    def _load_templates(self):
        """Load templates from disk."""
        templates_file = self.templates_dir / "templates.json"
        if templates_file.exists():
            try:
                with open(templates_file) as f:
                    data = json.load(f)
                    for template_data in data:
                        template = ContentTemplate.from_dict(template_data)
                        self._templates[template.id] = template
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse templates.json: {e}")
            except KeyError as e:
                logger.warning(f"Invalid template data (missing key): {e}")
            except OSError as e:
                logger.warning(f"Failed to load templates (I/O error): {e}")
            except Exception as e:
                logger.warning(f"Failed to load templates ({type(e).__name__}): {e}")
                logger.debug(traceback.format_exc())

    def _save_templates(self):
        """Save templates to disk."""
        templates_file = self.templates_dir / "templates.json"
        try:
            data = [t.to_dict() for t in self._templates.values()]
            with open(templates_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.warning(f"Failed to save templates (I/O error): {e}")
        except Exception as e:
            logger.warning(f"Failed to save templates ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())

    def _ensure_builtins(self):
        """Ensure built-in templates exist."""
        for builtin in self.BUILTIN_TEMPLATES:
            if builtin["id"] not in self._templates:
                template = ContentTemplate(
                    id=builtin["id"],
                    name=builtin["name"],
                    type=builtin["type"],
                    description=builtin.get("description", ""),
                    script_template=builtin.get("script_template", ""),
                    caption_template=builtin.get("caption_template", ""),
                    hashtags=builtin.get("hashtags", []),
                    music_style=builtin.get("music_style"),
                    duration_target=builtin.get("duration_target", 60),
                    category=builtin.get("category", "general"),
                    tags=["builtin"],
                )
                self._templates[template.id] = template

        self._save_templates()

    def create_template(
        self,
        name: str,
        type: Literal["video", "caption", "campaign", "post"],
        script_template: str = "",
        caption_template: str = "",
        hashtags: list[str] | None = None,
        music_style: str | None = None,
        voice_profile: str | None = None,
        visual_style: str | None = None,
        duration_target: int = 60,
        platform: str = "instagram",
        description: str = "",
        category: str = "custom",
        tags: list[str] | None = None,
    ) -> ContentTemplate:
        """
        Create a new content template.

        Args:
            name: Template name.
            type: Template type (video, caption, campaign, post).
            script_template: Script with {placeholders}.
            caption_template: Caption with {placeholders}.
            hashtags: Default hashtags.
            music_style: Preferred music style.
            voice_profile: Voice profile name.
            visual_style: Visual style preset.
            duration_target: Target duration in seconds.
            platform: Target platform.
            description: Template description.
            category: Category for organization.
            tags: Tags for filtering.

        Returns:
            Created ContentTemplate.
        """
        # Generate unique ID
        import hashlib

        id_base = f"{name}_{datetime.now().isoformat()}"
        template_id = hashlib.md5(id_base.encode()).hexdigest()[:12]

        template = ContentTemplate(
            id=template_id,
            name=name,
            type=type,
            description=description,
            script_template=script_template,
            caption_template=caption_template,
            hashtags=hashtags or [],
            music_style=music_style,
            voice_profile=voice_profile,
            visual_style=visual_style,
            duration_target=duration_target,
            platform=platform,
            category=category,
            tags=tags or [],
        )

        self._templates[template_id] = template
        self._save_templates()

        logger.info(f"📄 Created template: {name} ({template_id})")
        return template

    def get_template(self, template_id: str) -> ContentTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def update_template(self, template_id: str, **updates) -> ContentTemplate | None:
        """Update a template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = datetime.now().isoformat()
        self._save_templates()

        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            self._save_templates()
            logger.info(f"🗑️ Deleted template: {template_id}")
            return True
        return False

    def list_templates(
        self,
        type: str | None = None,
        category: str | None = None,
        search: str | None = None,
    ) -> list[ContentTemplate]:
        """
        List templates with optional filtering.

        Args:
            type: Filter by template type.
            category: Filter by category.
            search: Search in name and description.

        Returns:
            List of matching templates.
        """
        templates = list(self._templates.values())

        if type:
            templates = [t for t in templates if t.type == type]

        if category:
            templates = [t for t in templates if t.category == category]

        if search:
            search_lower = search.lower()
            templates = [
                t
                for t in templates
                if search_lower in t.name.lower()
                or search_lower in t.description.lower()
            ]

        # Sort by use count (most used first)
        templates.sort(key=lambda t: -t.use_count)

        return templates

    def apply_template(
        self,
        template_id: str,
        variables: dict[str, str],
    ) -> dict[str, Any]:
        """
        Apply a template with variables.

        Args:
            template_id: Template ID to apply.
            variables: Dict mapping placeholder names to values.

        Returns:
            Dict with filled script, caption, and settings.
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        def fill_template(text: str, vars: dict) -> str:
            """Replace {placeholders} with values."""
            for key, value in vars.items():
                text = text.replace(f"{{{key}}}", str(value))
            return text

        script = fill_template(template.script_template, variables)
        caption = fill_template(template.caption_template, variables)

        # Increment use count
        template.use_count += 1
        self._save_templates()

        return {
            "script": script,
            "caption": caption,
            "hashtags": template.hashtags.copy(),
            "music_style": template.music_style,
            "voice_profile": template.voice_profile,
            "visual_style": template.visual_style,
            "duration_target": template.duration_target,
            "platform": template.platform,
            "template_id": template_id,
            "template_name": template.name,
        }

    def get_placeholders(self, template_id: str) -> list[str]:
        """Get list of placeholders in a template."""
        template = self._templates.get(template_id)
        if not template:
            return []

        # Find all {placeholder} patterns
        text = template.script_template + " " + template.caption_template
        placeholders = re.findall(r"\{(\w+)\}", text)

        return list(set(placeholders))

    def duplicate_template(
        self,
        template_id: str,
        new_name: str,
    ) -> ContentTemplate | None:
        """Duplicate an existing template."""
        original = self._templates.get(template_id)
        if not original:
            return None

        return self.create_template(
            name=new_name,
            type=original.type,
            script_template=original.script_template,
            caption_template=original.caption_template,
            hashtags=original.hashtags.copy(),
            music_style=original.music_style,
            voice_profile=original.voice_profile,
            visual_style=original.visual_style,
            duration_target=original.duration_target,
            platform=original.platform,
            description=f"Copy of {original.name}",
            category=original.category,
            tags=original.tags.copy(),
        )

    def export_templates(self, template_ids: list[str] | None = None) -> dict:
        """Export templates as JSON-serializable dict."""
        if template_ids:
            templates = [
                self._templates[tid].to_dict()
                for tid in template_ids
                if tid in self._templates
            ]
        else:
            templates = [t.to_dict() for t in self._templates.values()]

        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "templates": templates,
        }

    def import_templates(
        self,
        data: dict,
        overwrite: bool = False,
    ) -> int:
        """
        Import templates from exported data.

        Args:
            data: Exported template data.
            overwrite: Whether to overwrite existing templates.

        Returns:
            Number of templates imported.
        """
        imported = 0

        for template_data in data.get("templates", []):
            template_id = template_data.get("id")

            if template_id in self._templates and not overwrite:
                continue

            template = ContentTemplate.from_dict(template_data)
            self._templates[template.id] = template
            imported += 1

        self._save_templates()
        logger.info(f"📥 Imported {imported} templates")

        return imported


# Convenience functions
def get_template_manager() -> TemplateManager:
    """Get the global template manager."""
    global _template_manager
    if "_template_manager" not in globals():
        _template_manager = TemplateManager()
    return _template_manager


def apply_template(template_id: str, variables: dict) -> dict:
    """Quick function to apply a template."""
    return get_template_manager().apply_template(template_id, variables)
