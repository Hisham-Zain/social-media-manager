"""
Edit Decision List (EDL) System for AgencyOS.

Non-destructive video editing through a JSON-based decision list.
Enables conversational editing ("swap scene 3") without re-rendering.

Features:
- ClipSegment dataclass for individual edits
- EditDecisionList for complete project state
- Export to MoviePy or FFmpeg for rendering
- JSON serialization for persistence
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from loguru import logger


@dataclass
class ClipSegment:
    """
    A single segment in the Edit Decision List.

    Represents one clip with timing, filters, and transitions.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    asset_path: str = ""
    start_time: float = 0.0
    end_time: float = 3.0
    filters: list[str] = field(default_factory=list)
    transition_in: str = "cut"  # cut, fade, dissolve, wipe
    transition_out: str = "cut"
    layer: int = 0  # For compositing (0 = base layer)
    volume: float = 1.0  # Audio volume multiplier
    speed: float = 1.0  # Playback speed
    position: tuple[int, int] = (0, 0)  # x, y offset
    scale: float = 1.0  # Scale factor
    opacity: float = 1.0  # Transparency

    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return max(0, self.end_time - self.start_time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "asset_path": self.asset_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "filters": self.filters,
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "layer": self.layer,
            "volume": self.volume,
            "speed": self.speed,
            "position": list(self.position),
            "scale": self.scale,
            "opacity": self.opacity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClipSegment":
        """Deserialize from dictionary."""
        pos = data.get("position", [0, 0])
        return cls(
            id=data.get("id", str(uuid4())),
            asset_path=data.get("asset_path", ""),
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", 3.0),
            filters=data.get("filters", []),
            transition_in=data.get("transition_in", "cut"),
            transition_out=data.get("transition_out", "cut"),
            layer=data.get("layer", 0),
            volume=data.get("volume", 1.0),
            speed=data.get("speed", 1.0),
            position=(pos[0], pos[1]) if len(pos) >= 2 else (0, 0),
            scale=data.get("scale", 1.0),
            opacity=data.get("opacity", 1.0),
        )


class EditDecisionList:
    """
    Non-destructive Edit Decision List.

    Stores editing decisions as a modifiable structure, enabling:
    - Conversational editing ("swap scene 3 for something faster")
    - Undo/redo without re-rendering
    - Export to MoviePy or FFmpeg for final render

    Example:
        edl = EditDecisionList("My Project")
        edl.add_segment(ClipSegment(asset_path="intro.mp4", end_time=5.0))
        edl.add_segment(ClipSegment(asset_path="main.mp4", end_time=30.0))

        # Conversational edit
        edl.update_segment(0, end_time=3.0)  # Shorten intro
        edl.swap_segment(1, "faster_main.mp4")  # Replace main clip

        # Render
        final_video = edl.to_moviepy()
        final_video.write_videofile("output.mp4")
    """

    def __init__(self, project_name: str = "Untitled") -> None:
        """
        Initialize an Edit Decision List.

        Args:
            project_name: Name for the project.
        """
        self.id = str(uuid4())
        self.project_name = project_name
        self.segments: list[ClipSegment] = []
        self.audio_segments: list[ClipSegment] = []
        self.output_resolution: tuple[int, int] = (1920, 1080)
        self.fps: int = 30
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()

    # --- Segment Management ---

    def add_segment(self, segment: ClipSegment, track: str = "video") -> int:
        """
        Add a segment to the EDL.

        Args:
            segment: ClipSegment to add.
            track: "video" or "audio".

        Returns:
            Index of the added segment.
        """
        target = self.audio_segments if track == "audio" else self.segments
        target.append(segment)
        self._mark_modified()
        logger.debug(f"📼 Added segment: {segment.asset_path}")
        return len(target) - 1

    def get_segment(self, index: int, track: str = "video") -> ClipSegment | None:
        """Get a segment by index."""
        target = self.audio_segments if track == "audio" else self.segments
        if 0 <= index < len(target):
            return target[index]
        return None

    def update_segment(
        self, index: int, track: str = "video", **kwargs: Any
    ) -> ClipSegment | None:
        """
        Update a segment's properties.

        Args:
            index: Segment index.
            track: "video" or "audio".
            **kwargs: Properties to update.

        Returns:
            Updated segment or None if not found.
        """
        segment = self.get_segment(index, track)
        if segment:
            for key, value in kwargs.items():
                if hasattr(segment, key):
                    setattr(segment, key, value)
            self._mark_modified()
            logger.debug(f"✏️ Updated segment {index}: {kwargs}")
        return segment

    def swap_segment(
        self, index: int, new_asset: str, track: str = "video"
    ) -> ClipSegment | None:
        """
        Swap a segment's asset while preserving timing and effects.

        Args:
            index: Segment index.
            new_asset: Path to new asset file.
            track: "video" or "audio".

        Returns:
            Updated segment or None if not found.
        """
        return self.update_segment(index, track, asset_path=new_asset)

    def remove_segment(self, index: int, track: str = "video") -> bool:
        """
        Remove a segment by index.

        Args:
            index: Segment index.
            track: "video" or "audio".

        Returns:
            True if removed, False if not found.
        """
        target = self.audio_segments if track == "audio" else self.segments
        if 0 <= index < len(target):
            target.pop(index)
            self._mark_modified()
            return True
        return False

    def reorder_segment(
        self, from_index: int, to_index: int, track: str = "video"
    ) -> bool:
        """
        Move a segment to a new position.

        Args:
            from_index: Current index.
            to_index: Target index.
            track: "video" or "audio".

        Returns:
            True if moved, False if invalid indices.
        """
        target = self.audio_segments if track == "audio" else self.segments
        if 0 <= from_index < len(target) and 0 <= to_index < len(target):
            segment = target.pop(from_index)
            target.insert(to_index, segment)
            self._mark_modified()
            return True
        return False

    def _mark_modified(self) -> None:
        """Update modification timestamp."""
        self.modified_at = datetime.now().isoformat()

    # --- Computed Properties ---

    @property
    def total_duration(self) -> float:
        """Calculate total duration of all segments."""
        return sum(seg.duration for seg in self.segments)

    @property
    def segment_count(self) -> int:
        """Get number of video segments."""
        return len(self.segments)

    # --- Serialization ---

    def to_dict(self) -> dict[str, Any]:
        """Serialize EDL to dictionary."""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "segments": [s.to_dict() for s in self.segments],
            "audio_segments": [s.to_dict() for s in self.audio_segments],
            "output_resolution": list(self.output_resolution),
            "fps": self.fps,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize EDL to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EditDecisionList":
        """Deserialize from dictionary."""
        edl = cls(project_name=data.get("project_name", "Untitled"))
        edl.id = data.get("id", str(uuid4()))
        edl.segments = [ClipSegment.from_dict(s) for s in data.get("segments", [])]
        edl.audio_segments = [
            ClipSegment.from_dict(s) for s in data.get("audio_segments", [])
        ]
        res = data.get("output_resolution", [1920, 1080])
        edl.output_resolution = (res[0], res[1])
        edl.fps = data.get("fps", 30)
        edl.created_at = data.get("created_at", datetime.now().isoformat())
        edl.modified_at = data.get("modified_at", datetime.now().isoformat())
        return edl

    @classmethod
    def from_json(cls, json_str: str) -> "EditDecisionList":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save(self, path: Path | str) -> None:
        """Save EDL to a JSON file."""
        path = Path(path)
        path.write_text(self.to_json())
        logger.info(f"💾 EDL saved to {path}")

    @classmethod
    def load(cls, path: Path | str) -> "EditDecisionList":
        """Load EDL from a JSON file."""
        path = Path(path)
        return cls.from_json(path.read_text())

    # --- Rendering ---

    def to_moviepy(self) -> Any:
        """
        Compile EDL to MoviePy CompositeVideoClip.

        Returns:
            CompositeVideoClip ready for rendering, or None if empty.
        """
        try:
            from moviepy import (
                CompositeVideoClip,
                VideoFileClip,
                concatenate_videoclips,
            )
        except ImportError:
            logger.error("❌ MoviePy not installed. Run: pip install moviepy")
            return None

        if not self.segments:
            logger.warning("⚠️ No segments to render")
            return None

        clips = []
        for seg in self.segments:
            if not Path(seg.asset_path).exists():
                logger.warning(f"⚠️ Asset not found: {seg.asset_path}")
                continue

            try:
                clip = VideoFileClip(seg.asset_path)

                # Apply subclip
                if seg.end_time > 0:
                    clip = clip.subclip(
                        seg.start_time, min(seg.end_time, clip.duration)
                    )

                # Apply speed
                if seg.speed != 1.0:
                    clip = clip.speedx(seg.speed)

                # Apply filters
                for f in seg.filters:
                    clip = self._apply_filter(clip, f)

                clips.append(clip)
            except Exception as e:
                logger.error(f"❌ Failed to process {seg.asset_path}: {e}")

        if not clips:
            return None

        return concatenate_videoclips(clips)

    def _apply_filter(self, clip: Any, filter_name: str) -> Any:
        """Apply a named filter to a clip."""
        try:
            if filter_name == "grayscale":
                return clip.fx(
                    lambda c: c.to_RGB().fx(
                        lambda x: x.fl_image(
                            lambda img: img.convert("L").convert("RGB")
                        )
                    )
                )
            elif filter_name == "mirror":
                return clip.fx(lambda c: c.fl_image(lambda img: img.transpose(0)))
            # Add more filters as needed
        except Exception as e:
            logger.warning(f"⚠️ Filter '{filter_name}' failed: {e}")
        return clip

    def to_ffmpeg_cmd(self, output_path: str) -> str:
        """
        Generate FFmpeg command for rendering.

        Args:
            output_path: Path for output file.

        Returns:
            FFmpeg command string.
        """
        if not self.segments:
            return ""

        # Build filter complex for concatenation
        inputs = []
        filter_parts = []

        for i, seg in enumerate(self.segments):
            inputs.append(f'-i "{seg.asset_path}"')
            trim = f"[{i}:v]trim=start={seg.start_time}:end={seg.end_time},"
            trim += f"setpts=PTS-STARTPTS[v{i}]"
            filter_parts.append(trim)

        # Concatenate all streams
        concat_inputs = "".join(f"[v{i}]" for i in range(len(self.segments)))
        filter_parts.append(
            f"{concat_inputs}concat=n={len(self.segments)}:v=1:a=0[out]"
        )

        filter_complex = ";".join(filter_parts)

        cmd = (
            f"ffmpeg {' '.join(inputs)} "
            f'-filter_complex "{filter_complex}" '
            f'-map "[out]" -r {self.fps} '
            f"-s {self.output_resolution[0]}x{self.output_resolution[1]} "
            f'"{output_path}"'
        )

        return cmd


# --- Convenience Functions ---


def create_edl_from_assets(
    assets: list[str],
    project_name: str = "Quick Edit",
    segment_duration: float = 3.0,
) -> EditDecisionList:
    """
    Quick function to create an EDL from a list of assets.

    Args:
        assets: List of asset file paths.
        project_name: Name for the project.
        segment_duration: Default duration per segment.

    Returns:
        EditDecisionList with segments added.
    """
    edl = EditDecisionList(project_name)
    for asset in assets:
        edl.add_segment(ClipSegment(asset_path=asset, end_time=segment_duration))
    return edl
