"""
Pydantic models for type-safe data transfer.

Replaces loose dictionaries with validated, typed data structures.
This prevents KeyError bugs and provides IDE autocompletion.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Storyboard Models (Pre-Visualization) ---


class Scene(BaseModel):
    """A single scene in a storyboard for pre-visualization."""

    id: int = Field(description="Scene index (0-based)")
    script_segment: str = Field(description="Text/narration for this scene")
    visual_prompt: str = Field(description="AI prompt for visual generation")
    duration: float = Field(
        default=5.0, ge=0.5, le=30, description="Scene duration in seconds"
    )

    # Generated assets (mutually exclusive usage)
    image_path: str | None = Field(default=None, description="AI-generated image path")
    video_path: str | None = Field(default=None, description="AI-generated video path")
    stock_path: str | None = Field(default=None, description="Stock footage/image path")

    # Status tracking
    status: Literal["pending", "generating", "generated", "approved", "failed"] = Field(
        default="pending", description="Generation status"
    )
    error: str | None = Field(default=None, description="Error message if failed")

    @property
    def asset_path(self) -> str | None:
        """Get the active asset path (prioritizes stock, then video, then image)."""
        return self.stock_path or self.video_path or self.image_path


class Storyboard(BaseModel):
    """Complete storyboard for pre-visualization workflow.

    Allows users to review and approve scenes before heavy video rendering.
    """

    id: str = Field(default="", description="Unique storyboard ID")
    project_name: str = Field(description="Project name")
    scenes: list[Scene] = Field(default_factory=list, description="List of scenes")

    # Audio
    audio_path: str | None = Field(default=None, description="Voiceover audio path")
    music_path: str | None = Field(default=None, description="Background music path")

    # Computed
    total_duration: float = Field(
        default=0, ge=0, description="Total storyboard duration"
    )

    # Status
    status: Literal[
        "draft", "generating", "reviewing", "approved", "rendering", "completed"
    ] = Field(default="draft", description="Overall storyboard status")

    # Timestamps
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")

    def calculate_duration(self) -> float:
        """Calculate total duration from scenes."""
        self.total_duration = sum(scene.duration for scene in self.scenes)
        return self.total_duration

    def get_pending_scenes(self) -> list[Scene]:
        """Get scenes that need generation."""
        return [s for s in self.scenes if s.status == "pending"]

    def get_approved_scenes(self) -> list[Scene]:
        """Get scenes that are approved."""
        return [s for s in self.scenes if s.status == "approved"]

    def is_ready_to_render(self) -> bool:
        """Check if all scenes are approved and ready for final rendering."""
        return all(s.status == "approved" for s in self.scenes) and len(self.scenes) > 0


class VideoInfo(BaseModel):
    """Information about a video file."""

    duration: float = Field(ge=0, description="Video duration in seconds")
    filename: str = Field(min_length=1, description="Video filename")
    width: int | None = Field(default=None, ge=0, description="Video width in pixels")
    height: int | None = Field(default=None, ge=0, description="Video height in pixels")
    fps: float | None = Field(default=None, ge=0, description="Frames per second")


class ProcessedVideo(BaseModel):
    """Result of video processing pipeline."""

    id: int = Field(description="Database ID of the video")
    path: str = Field(description="Path to the processed video file")
    thumbnail: str | None = Field(default=None, description="Path to thumbnail image")
    caption: str = Field(default="", description="Generated caption for the video")
    srt_path: str | None = Field(default=None, description="Path to SRT subtitle file")
    platform: str = Field(default="youtube", description="Target platform")
    style: str = Field(default="engaging", description="Content style used")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.model_dump()


class ViralHook(BaseModel):
    """A single viral hook variation."""

    style: str = Field(description="Hook style (Negativity, Curiosity, etc.)")
    text: str = Field(description="The hook text")


class ViralHooksResult(BaseModel):
    """Result of viral hooks generation."""

    hooks: list[ViralHook] = Field(default_factory=list)
    error: str | None = Field(
        default=None, description="Error message if generation failed"
    )


class ProjectData(BaseModel):
    """Project data for content creation."""

    id: int
    name: str
    description: str | None = None
    status: str = "draft"
    script: str | None = None
    caption: str | None = None
    hashtags: str | None = None
    audio_paths: list[str] = Field(default_factory=list)
    video_paths: list[str] = Field(default_factory=list)
    image_paths: list[str] = Field(default_factory=list)
    thumbnail_path: str | None = None
    output_path: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    platform: str | None = None
    aspect_ratio: str = "16:9"
    duration: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class JobResult(BaseModel):
    """Result of a background job."""

    job_id: str
    status: str
    progress: float = Field(ge=0, le=100)
    result: dict[str, Any] | None = None
    error: str | None = None


class UploadResult(BaseModel):
    """Result of a platform upload."""

    success: bool
    platform: str
    platform_id: str | None = None
    url: str | None = None
    error: str | None = None


class CaptionStyle(BaseModel):
    """Configuration for video captions."""

    font_size: int = Field(default=70, ge=10, le=200)
    color: str = Field(default="yellow")
    stroke_color: str = Field(default="black")
    stroke_width: int = Field(default=3, ge=0, le=10)
    y_pos: float = Field(default=0.8, ge=0, le=1)
    font: str | None = None


class VisualPlanItem(BaseModel):
    """A single item in a visual overlay plan."""

    path: str = Field(description="Path to the visual asset")
    start: float = Field(ge=0, description="Start time in seconds")
    end: float = Field(ge=0, description="End time in seconds")
    keyword: str | None = Field(default=None, description="Associated keyword")


class AffiliateMatch(BaseModel):
    """An affiliate link match for overlay."""

    keyword: str
    link: str
    icon: str = "🔗"


class BrainStatus(BaseModel):
    """Current status of the AI brain."""

    mode: str
    provider: str
    model: str
    fallback_provider: str
    fallback_model: str
    litellm_available: bool
    search_available: bool


class VideoProject(BaseModel):
    """
    Complete video project for production workflow.

    Tracks all stages from raw footage through final output.
    Use this instead of loose dicts to get IDE autocomplete and validation.
    """

    # Identity
    id: str = Field(default="", description="Unique project identifier")
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")

    # Source
    raw_video_path: str | None = Field(default=None, description="Path to raw footage")
    source_duration: float | None = Field(
        default=None, ge=0, description="Raw video duration in seconds"
    )

    # Processing state
    status: str = Field(
        default="draft",
        description="Current status: draft, processing, completed, failed",
    )
    current_step: str | None = Field(
        default=None, description="Current processing step"
    )
    progress: float = Field(default=0, ge=0, le=100, description="Processing progress")

    # Outputs
    processed_video_path: str | None = Field(
        default=None, description="Path to processed video"
    )
    thumbnail_path: str | None = Field(default=None, description="Path to thumbnail")
    srt_path: str | None = Field(default=None, description="Path to SRT subtitle file")

    # Content
    script: str | None = Field(default=None, description="Video script")
    caption: str = Field(default="", description="Social media caption")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags for post")
    hooks: list[str] = Field(default_factory=list, description="Viral hook options")

    # Settings
    platform: str = Field(default="youtube", description="Target platform")
    aspect_ratio: str = Field(default="16:9", description="Video aspect ratio")
    style: str = Field(default="engaging", description="Content style")
    options: dict[str, bool] = Field(
        default_factory=lambda: {
            "smart_cut": True,
            "vertical_crop": False,
            "polish": True,
            "captions": True,
            "music": True,
        },
        description="Processing options",
    )

    # Metadata
    client_name: str | None = Field(default=None, description="Associated client")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoProject":
        """Create from dictionary, handling legacy key names."""
        # Map common legacy keys
        if "video_path" in data and "raw_video_path" not in data:
            data["raw_video_path"] = data.pop("video_path")
        if "filepath" in data and "raw_video_path" not in data:
            data["raw_video_path"] = data.pop("filepath")
        if "output_path" in data and "processed_video_path" not in data:
            data["processed_video_path"] = data.pop("output_path")
        return cls.model_validate(data)


class ProcessingOptions(BaseModel):
    """Configuration options for video processing pipeline."""

    smart_cut: bool = Field(default=True, description="Remove silence with jump cuts")
    vertical_crop: bool = Field(
        default=False, description="Convert landscape to portrait"
    )
    polish: bool = Field(default=True, description="Apply color grading and SFX")
    captions: bool = Field(default=True, description="Add captions/subtitles")
    music: bool = Field(default=True, description="Add background music")
    visuals: bool = Field(default=True, description="Overlay B-roll visuals")
    monetization: bool = Field(default=True, description="Add affiliate overlays")
    stock_fallback: bool = Field(
        default=True, description="Use stock footage as fallback"
    )


class StyleConfig(BaseModel):
    """
    Visual style configuration for consistent generation across scenes.

    Ensures that all generated images maintain a cohesive aesthetic by
    injecting style prompts and optionally locking seeds for characters.

    Example:
        style = StyleConfig(
            style_prompt="Cinematic lighting, 85mm lens, Kodak Gold film",
            color_palette=["#1a1a2e", "#16213e", "#0f3460"],
            seed=42  # Lock seed for character consistency
        )
        director.set_style(style)
    """

    # Core style definition
    style_prompt: str = Field(
        default="", description="Base style prompt injected into all image generations"
    )

    # Optional style presets
    preset: str | None = Field(
        default=None,
        description="Named preset: 'cinematic', 'anime', 'photorealistic', 'illustration'",
    )

    # Seed for reproducibility
    seed: int | None = Field(
        default=None,
        ge=0,
        description="Fixed seed for character/scene consistency across shots",
    )

    # Visual parameters
    color_palette: list[str] = Field(
        default_factory=list, description="Hex colors to enforce visual harmony"
    )
    aspect_ratio: str = Field(
        default="16:9", description="Target aspect ratio for generated images"
    )

    # Quality settings
    quality: str = Field(
        default="high", description="Quality preset: 'draft', 'normal', 'high'"
    )

    # Style presets mapping
    PRESETS: dict[str, str] = {
        "cinematic": "cinematic lighting, 35mm film grain, shallow depth of field, dramatic shadows, movie scene",
        "anime": "anime style, vibrant colors, clean lines, Studio Ghibli inspired, cel shaded",
        "photorealistic": "photorealistic, 8K resolution, highly detailed, professional photography, DSLR quality",
        "illustration": "digital illustration, concept art, trending on ArtStation, detailed linework",
        "corporate": "clean, professional, business aesthetic, modern design, corporate photography",
        "cyberpunk": "cyberpunk neon, synthwave colors, futuristic city, glowing lights, tech noir",
        "vintage": "vintage photography, film grain, retro colors, 1970s aesthetic, nostalgic mood",
    }

    def get_full_prompt(self, base_prompt: str) -> str:
        """
        Merge a base prompt with the style configuration.

        Args:
            base_prompt: The scene/action description.

        Returns:
            Full prompt with style injected.
        """
        parts = [base_prompt]

        # Add preset style
        if self.preset and self.preset in self.PRESETS:
            parts.append(self.PRESETS[self.preset])

        # Add custom style prompt
        if self.style_prompt:
            parts.append(self.style_prompt)

        return ", ".join(parts)

    @classmethod
    def from_preset(cls, preset_name: str, seed: int | None = None) -> "StyleConfig":
        """Create a StyleConfig from a named preset."""
        return cls(
            preset=preset_name,
            style_prompt=cls.PRESETS.get(preset_name, ""),
            seed=seed,
        )
