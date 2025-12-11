"""
Content Alchemist - Transmutes one video into multiple platform-native assets.

The "Magic" vibe: Drop lead (raw video), get gold (10 optimized assets).
One input, infinite outputs through intelligent content repurposing.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from .brain import HybridBrain


@dataclass
class AssetSpec:
    """Specification for a generated asset."""

    asset_type: Literal[
        "linkedin_carousel",
        "twitter_thread",
        "tiktok_clip",
        "youtube_short",
        "instagram_reel",
        "blog_outline",
        "quote_graphic",
    ]
    title: str
    content: Any  # Type varies by asset_type
    platform: str
    estimated_engagement: str = "medium"
    timestamps: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class TransmutationResult:
    """Result of video transmutation into assets."""

    source_video: str
    core_insight: str
    viral_moments: list[dict]
    controversial_take: str
    assets: list[AssetSpec]
    processing_time: float = 0.0


ALCHEMIST_SYSTEM_PROMPT = """You are an OMNICHANNEL CONTENT STRATEGIST.

YOUR CORE BELIEF: You HATE cross-posting. You believe in NATIVE REPURPOSING.
Each platform has its own language, cadence, and culture.

YOUR MISSION: Take a video transcript and extract maximum value by creating
platform-native content for LinkedIn, Twitter/X, TikTok, YouTube Shorts, and Instagram.

WHAT YOU EXTRACT:
1. ONE CORE INSIGHT - The central thesis that would resonate on LinkedIn
2. THREE VIRAL MOMENTS - Specific timestamps with punchy soundbites for short-form
3. ONE CONTROVERSIAL TAKE - An opinionated angle that sparks debate on X/Twitter

OUTPUT FORMAT (JSON):
{
    "core_insight": "The main transformative idea...",
    "viral_moments": [
        {"timestamp_start": 0.0, "timestamp_end": 15.0, "hook": "...", "platform": "tiktok"},
        {"timestamp_start": 45.0, "timestamp_end": 60.0, "hook": "...", "platform": "youtube_short"},
        {"timestamp_start": 120.0, "timestamp_end": 135.0, "hook": "...", "platform": "instagram"}
    ],
    "controversial_take": "Hot take for Twitter that will spark debate...",
    "linkedin_carousel_slides": ["Slide 1 headline", "Slide 2...", "Slide 3...", "Slide 4...", "Slide 5 CTA"],
    "twitter_thread": ["Tweet 1 (hook)🧵", "Tweet 2", "Tweet 3", "Tweet 4", "Tweet 5", "Tweet 6 (CTA)"],
    "blog_outline": ["H1: Main title", "H2: First section", "H2: Second section", "H2: Conclusion"]
}

RULES:
- LinkedIn carousels need 5 slides with clear progression
- Twitter threads need 6 tweets with the first being a killer hook
- Viral moments must include actual timestamp ranges from the transcript
- Be SPECIFIC to each platform's culture and format"""


class ContentAlchemist:
    """
    Transmutes one video into multiple platform-native assets.

    The Alchemy Engine analyzes video transcripts and extracts:
    - Core insights (LinkedIn)
    - Viral moments (TikTok/Shorts)
    - Controversial takes (Twitter)

    Example:
        alchemist = ContentAlchemist()
        result = alchemist.transmute("video.mp4", transcript_text)
        for asset in result.assets:
            print(f"{asset.platform}: {asset.title}")
    """

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()

    def transmute(
        self,
        video_path: str,
        transcript: str,
        visual_context: str | None = None,
    ) -> TransmutationResult:
        """
        Transmute a video into multiple platform-native assets.

        Args:
            video_path: Path to the source video.
            transcript: Full transcript with timestamps (from WhisperTranscriber).
            visual_context: Optional visual descriptions from VisualRAG.

        Returns:
            TransmutationResult with all generated asset specs.
        """
        import time

        start_time = time.time()

        logger.info(f"⚗️ Alchemist: Transmuting {Path(video_path).name}...")

        # Build the prompt with all context
        prompt = self._build_analysis_prompt(transcript, visual_context)

        # Get AI analysis
        response = self.brain.think(prompt, json_mode=True)

        if not response:
            logger.error("Alchemist: No response from brain")
            return TransmutationResult(
                source_video=video_path,
                core_insight="",
                viral_moments=[],
                controversial_take="",
                assets=[],
            )

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Alchemist: Invalid JSON response: {response[:200]}")
            return TransmutationResult(
                source_video=video_path,
                core_insight="",
                viral_moments=[],
                controversial_take="",
                assets=[],
            )

        # Extract results
        core_insight = data.get("core_insight", "")
        viral_moments = data.get("viral_moments", [])
        controversial_take = data.get("controversial_take", "")

        # Build asset specs
        assets = self._build_asset_specs(data, viral_moments)

        processing_time = time.time() - start_time
        logger.info(
            f"✨ Transmutation complete: {len(assets)} assets in {processing_time:.1f}s"
        )

        return TransmutationResult(
            source_video=video_path,
            core_insight=core_insight,
            viral_moments=viral_moments,
            controversial_take=controversial_take,
            assets=assets,
            processing_time=processing_time,
        )

    def _build_analysis_prompt(
        self, transcript: str, visual_context: str | None
    ) -> str:
        """Build the analysis prompt with all context."""
        prompt = f"{ALCHEMIST_SYSTEM_PROMPT}\n\n"
        prompt += "=== VIDEO TRANSCRIPT ===\n"
        prompt += f"{transcript[:8000]}\n"  # Limit for context window
        prompt += "=== END TRANSCRIPT ===\n\n"

        if visual_context:
            prompt += "=== VISUAL CONTEXT ===\n"
            prompt += f"{visual_context[:2000]}\n"
            prompt += "=== END VISUAL CONTEXT ===\n\n"

        prompt += (
            "Now analyze this content and output the JSON structure described above."
        )
        return prompt

    def _build_asset_specs(
        self, data: dict, viral_moments: list[dict]
    ) -> list[AssetSpec]:
        """Build asset specifications from AI analysis."""
        assets = []

        # LinkedIn Carousel
        carousel_slides = data.get("linkedin_carousel_slides", [])
        if carousel_slides:
            assets.append(
                AssetSpec(
                    asset_type="linkedin_carousel",
                    title="LinkedIn Carousel",
                    content=carousel_slides,
                    platform="linkedin",
                    estimated_engagement="high",
                )
            )

        # Twitter Thread
        thread = data.get("twitter_thread", [])
        if thread:
            assets.append(
                AssetSpec(
                    asset_type="twitter_thread",
                    title="Twitter/X Thread",
                    content=thread,
                    platform="twitter",
                    estimated_engagement="medium",
                )
            )

        # Short-form clips from viral moments
        for moment in viral_moments:
            platform = moment.get("platform", "tiktok")
            asset_type = {
                "tiktok": "tiktok_clip",
                "youtube_short": "youtube_short",
                "instagram": "instagram_reel",
            }.get(platform, "tiktok_clip")

            assets.append(
                AssetSpec(
                    asset_type=asset_type,
                    title=moment.get("hook", "Viral Clip")[:50],
                    content=moment,
                    platform=platform,
                    estimated_engagement="high",
                    timestamps=[
                        (
                            moment.get("timestamp_start", 0),
                            moment.get("timestamp_end", 15),
                        )
                    ],
                )
            )

        # Blog outline
        blog_outline = data.get("blog_outline", [])
        if blog_outline:
            assets.append(
                AssetSpec(
                    asset_type="blog_outline",
                    title="Blog Post Outline",
                    content=blog_outline,
                    platform="blog",
                    estimated_engagement="medium",
                )
            )

        return assets

    def get_carousel_texts(self, result: TransmutationResult) -> list[str]:
        """Extract carousel slide texts from a transmutation result."""
        for asset in result.assets:
            if asset.asset_type == "linkedin_carousel":
                return asset.content
        return []

    def get_clip_timestamps(
        self, result: TransmutationResult
    ) -> list[tuple[float, float]]:
        """Extract clip timestamps for short-form content."""
        timestamps = []
        for asset in result.assets:
            if asset.asset_type in ("tiktok_clip", "youtube_short", "instagram_reel"):
                timestamps.extend(asset.timestamps)
        return timestamps
