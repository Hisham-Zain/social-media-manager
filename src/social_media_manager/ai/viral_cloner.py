"""
ViralCloner: Competitor Content Reverse Engineering Agent.

Analyzes viral videos to extract reusable patterns:
- Script structure and hooks
- Visual rhythm and pacing
- Audio patterns
- Outputs as ContentTemplate
"""

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class VideoAnalysis:
    """Analysis result for a viral video."""

    url: str
    title: str = ""
    duration: float = 0.0
    platform: str = ""

    # Content analysis
    transcript: str = ""
    hook: str = ""
    structure: list[str] = field(default_factory=list)
    call_to_action: str = ""

    # Visual analysis
    scene_count: int = 0
    avg_scene_duration: float = 0.0
    visual_style: str = ""
    transitions: list[str] = field(default_factory=list)

    # Audio analysis
    music_style: str = ""
    voice_tone: str = ""
    has_captions: bool = False

    # Engagement signals
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    engagement_rate: float = 0.0

    # Extracted patterns
    hashtags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "duration": self.duration,
            "platform": self.platform,
            "transcript": self.transcript,
            "hook": self.hook,
            "structure": self.structure,
            "call_to_action": self.call_to_action,
            "scene_count": self.scene_count,
            "avg_scene_duration": self.avg_scene_duration,
            "visual_style": self.visual_style,
            "transitions": self.transitions,
            "music_style": self.music_style,
            "voice_tone": self.voice_tone,
            "has_captions": self.has_captions,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "engagement_rate": self.engagement_rate,
            "hashtags": self.hashtags,
            "keywords": self.keywords,
        }


class ViralCloner:
    """
    Reverse engineer viral content into reusable templates.

    Analyzes competitor videos to extract:
    - Script structure and hooks
    - Visual pacing and rhythm
    - Audio/music patterns
    - Engagement patterns

    Outputs as ContentTemplate for reproduction.

    Example:
        cloner = ViralCloner()

        # Analyze a viral video
        analysis = cloner.analyze_video("https://youtube.com/watch?v=...")

        # Generate template from analysis
        template = cloner.generate_template(analysis)
    """

    SUPPORTED_PLATFORMS = ["youtube", "tiktok", "instagram", "twitter"]

    def __init__(self) -> None:
        """Initialize the cloner."""
        self._brain = None
        self._visual_rag = None
        self._transcriber = None
        self._downloader_available = self._check_downloader()

    def _check_downloader(self) -> bool:
        """Check if yt-dlp is available."""
        try:
            import yt_dlp

            return True
        except ImportError:
            logger.warning("⚠️ yt-dlp not available. Install with: pip install yt-dlp")
            return False

    @property
    def brain(self):
        """Lazy-load HybridBrain."""
        if self._brain is None:
            from ..ai.brain import HybridBrain

            self._brain = HybridBrain()
        return self._brain

    @property
    def visual_rag(self):
        """Lazy-load VisualRAG."""
        if self._visual_rag is None:
            try:
                from ..ai.visual_rag import VisualRAG

                self._visual_rag = VisualRAG()
            except ImportError:
                logger.warning("⚠️ VisualRAG not available")
        return self._visual_rag

    def analyze_video(self, url: str) -> VideoAnalysis | None:
        """
        Analyze a video from URL.

        Downloads the video, extracts metadata, transcribes audio,
        and analyzes visual patterns.

        Args:
            url: Video URL (YouTube, TikTok, Instagram, etc.)

        Returns:
            VideoAnalysis with extracted patterns, or None if failed.
        """
        logger.info(f"🔍 Analyzing video: {url}")

        # Detect platform
        platform = self._detect_platform(url)
        if not platform:
            logger.error(f"❌ Unsupported platform for URL: {url}")
            return None

        analysis = VideoAnalysis(url=url, platform=platform)

        # Download video and get metadata
        video_path, metadata = self._download_video(url)
        if not video_path:
            logger.error("❌ Failed to download video")
            return None

        try:
            # Extract metadata
            analysis.title = metadata.get("title", "")
            analysis.duration = metadata.get("duration", 0)
            analysis.view_count = metadata.get("view_count", 0)
            analysis.like_count = metadata.get("like_count", 0)
            analysis.comment_count = metadata.get("comment_count", 0)

            # Calculate engagement rate
            if analysis.view_count > 0:
                analysis.engagement_rate = (
                    (analysis.like_count + analysis.comment_count)
                    / analysis.view_count
                    * 100
                )

            # Extract hashtags from description
            description = metadata.get("description", "")
            analysis.hashtags = self._extract_hashtags(description)

            # Transcribe audio
            analysis.transcript = self._transcribe_video(video_path)

            # Analyze transcript structure
            if analysis.transcript:
                structure = self._analyze_structure(analysis.transcript)
                analysis.hook = structure.get("hook", "")
                analysis.structure = structure.get("sections", [])
                analysis.call_to_action = structure.get("cta", "")
                analysis.keywords = structure.get("keywords", [])

            # Analyze visual patterns
            if self.visual_rag:
                visual = self._analyze_visuals(video_path)
                analysis.scene_count = visual.get("scene_count", 0)
                analysis.avg_scene_duration = visual.get("avg_scene_duration", 0)
                analysis.visual_style = visual.get("style", "")
                analysis.transitions = visual.get("transitions", [])

            # Analyze audio/music
            audio = self._analyze_audio(video_path)
            analysis.music_style = audio.get("music_style", "")
            analysis.voice_tone = audio.get("voice_tone", "")
            analysis.has_captions = audio.get("has_captions", False)

            logger.info(f"✅ Analysis complete: {analysis.title[:50]}...")
            return analysis

        finally:
            # Cleanup temporary video file
            if video_path and Path(video_path).exists():
                try:
                    Path(video_path).unlink()
                except Exception:
                    pass

    def generate_template(
        self,
        analysis: VideoAnalysis,
        template_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a ContentTemplate from video analysis.

        Args:
            analysis: VideoAnalysis from analyze_video().
            template_name: Optional custom template name.

        Returns:
            Template data dict ready for TemplateManager.create_template().
        """
        name = template_name or f"Clone: {analysis.title[:30]}..."

        # Build script template from structure
        script_parts = []

        if analysis.hook:
            script_parts.append(f"HOOK: {analysis.hook}")
            script_parts.append("")

        for i, section in enumerate(analysis.structure, 1):
            script_parts.append(f"SECTION {i}: {section}")

        if analysis.call_to_action:
            script_parts.append("")
            script_parts.append(f"CTA: {analysis.call_to_action}")

        script_template = "\n".join(script_parts)

        # Build caption template
        caption_template = self._generate_caption_template(analysis)

        template_data = {
            "name": name,
            "type": "video",
            "description": f"Cloned from: {analysis.url}",
            "script_template": script_template,
            "caption_template": caption_template,
            "hashtags": analysis.hashtags[:10],
            "music_style": analysis.music_style or "energetic",
            "visual_style": analysis.visual_style or "dynamic",
            "duration_target": int(analysis.duration) if analysis.duration else 60,
            "platform": analysis.platform,
            "category": "cloned",
            "tags": ["cloned", "viral", analysis.platform],
            "source_analysis": analysis.to_dict(),
        }

        logger.info(f"📄 Generated template: {name}")
        return template_data

    def clone_to_template_manager(
        self,
        url: str,
        template_name: str | None = None,
    ) -> str | None:
        """
        Full workflow: analyze video and create template.

        Args:
            url: Video URL to clone.
            template_name: Optional template name.

        Returns:
            Template ID if successful, None otherwise.
        """
        # Analyze
        analysis = self.analyze_video(url)
        if not analysis:
            return None

        # Generate template data
        template_data = self.generate_template(analysis, template_name)

        # Create via TemplateManager
        try:
            from .templates import get_template_manager

            manager = get_template_manager()
            template = manager.create_template(
                name=template_data["name"],
                type=template_data["type"],
                description=template_data["description"],
                script_template=template_data["script_template"],
                caption_template=template_data["caption_template"],
                hashtags=template_data["hashtags"],
                music_style=template_data["music_style"],
                visual_style=template_data["visual_style"],
                duration_target=template_data["duration_target"],
                platform=template_data["platform"],
                category=template_data["category"],
                tags=template_data["tags"],
            )

            logger.info(f"✅ Created template: {template.id}")
            return template.id

        except Exception as e:
            logger.error(f"❌ Failed to create template: {e}")
            return None

    # --- Private Methods ---

    def _detect_platform(self, url: str) -> str | None:
        """Detect platform from URL."""
        url_lower = url.lower()

        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "tiktok.com" in url_lower:
            return "tiktok"
        elif "instagram.com" in url_lower:
            return "instagram"
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"

        return None

    def _download_video(self, url: str) -> tuple[str | None, dict]:
        """Download video and return path + metadata."""
        if not self._downloader_available:
            return None, {}

        try:
            import yt_dlp

            # Create temp file
            temp_dir = tempfile.mkdtemp()
            output_path = Path(temp_dir) / "video.mp4"

            ydl_opts = {
                "format": "best[height<=720]",  # Limit quality for speed
                "outtmpl": str(output_path),
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                metadata = {
                    "title": info.get("title", ""),
                    "description": info.get("description", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "comment_count": info.get("comment_count", 0),
                    "uploader": info.get("uploader", ""),
                    "upload_date": info.get("upload_date", ""),
                }

            if output_path.exists():
                return str(output_path), metadata

            # yt-dlp may add extension
            for ext in [".mp4", ".webm", ".mkv"]:
                alt_path = output_path.with_suffix(ext)
                if alt_path.exists():
                    return str(alt_path), metadata

            return None, metadata

        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            return None, {}

    def _transcribe_video(self, video_path: str) -> str:
        """Transcribe video audio using Whisper."""
        try:
            # Try using our transcriber
            from ..ai.transcriber import WhisperTranscriber

            transcriber = WhisperTranscriber()
            result = transcriber.transcribe(video_path)
            return result.get("text", "")

        except ImportError:
            logger.warning("⚠️ Transcriber not available, using AI estimation")
            return ""
        except Exception as e:
            logger.warning(f"⚠️ Transcription failed: {e}")
            return ""

    def _analyze_structure(self, transcript: str) -> dict[str, Any]:
        """Use AI to analyze transcript structure."""
        if not transcript:
            return {}

        prompt = f"""Analyze this video transcript and extract:
1. The opening hook (first attention-grabbing sentence)
2. Main content sections (3-5 key points)
3. Call-to-action (CTA at the end)
4. Top 5 keywords

Transcript:
{transcript[:2000]}

Return JSON:
{{
    "hook": "...",
    "sections": ["section1", "section2", ...],
    "cta": "...",
    "keywords": ["word1", "word2", ...]
}}"""

        try:
            response = self.brain.think(prompt, json_mode=True)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"⚠️ Structure analysis failed: {e}")
            return {}

    def _analyze_visuals(self, video_path: str) -> dict[str, Any]:
        """Analyze visual patterns using VisualRAG."""
        if not self.visual_rag:
            return {}

        try:
            # Index video to extract frames
            frame_count = self.visual_rag.index_video(video_path)

            # Estimate scene info
            from moviepy import VideoFileClip

            clip = VideoFileClip(video_path)
            duration = clip.duration
            clip.close()

            avg_scene_duration = duration / max(frame_count, 1) if frame_count else 3.0

            # Use AI to describe visual style
            style_prompt = f"""Based on {frame_count} frames extracted from a {duration:.0f}s video,
describe the likely visual style in 2-3 words (e.g., "fast-paced dramatic", "calm aesthetic", "energetic colorful")."""

            style = self.brain.think(style_prompt).strip().strip('"')

            return {
                "scene_count": frame_count,
                "avg_scene_duration": avg_scene_duration,
                "style": style,
                "transitions": ["cut"],  # Default
            }

        except Exception as e:
            logger.warning(f"⚠️ Visual analysis failed: {e}")
            return {}

    def _analyze_audio(self, video_path: str) -> dict[str, Any]:
        """Analyze audio patterns."""
        # Simplified audio analysis
        return {
            "music_style": "background",
            "voice_tone": "conversational",
            "has_captions": False,
        }

    def _extract_hashtags(self, text: str) -> list[str]:
        """Extract hashtags from text."""
        hashtags = re.findall(r"#(\w+)", text)
        return list(set(hashtags))[:15]

    def _generate_caption_template(self, analysis: VideoAnalysis) -> str:
        """Generate caption template from analysis."""
        parts = []

        if analysis.hook:
            # Create placeholder version of hook
            hook_placeholder = re.sub(r"\b\w{5,}\b", "{topic}", analysis.hook, count=2)
            parts.append(hook_placeholder)
        else:
            parts.append("🔥 {topic}")

        parts.append("")
        parts.append("{main_point}")
        parts.append("")

        if analysis.call_to_action:
            cta_placeholder = re.sub(
                r"\b\w{5,}\b", "{action}", analysis.call_to_action, count=1
            )
            parts.append(cta_placeholder)
        else:
            parts.append("👇 {action}")

        return "\n".join(parts)


# Singleton
_viral_cloner: ViralCloner | None = None


def get_viral_cloner() -> ViralCloner:
    """Get the ViralCloner singleton."""
    global _viral_cloner
    if _viral_cloner is None:
        _viral_cloner = ViralCloner()
    return _viral_cloner
