"""
Video Production Pipeline for AgencyOS.

Complete end-to-end video production:
Script → TTS → Avatar → Music → Final Video

Orchestrates all AI modules into a single workflow.

Features:
- Checkpoint-based resumable production
- Automatic state persistence after each step
- Recovery from crash/interruption
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger

from ..config import config
from ..core.project_state import ProductionStep, ProjectManifest
from ..database import DatabaseManager


@dataclass
class VideoProject:
    """Container for all video production assets and settings."""

    # Basic info
    name: str
    description: str = ""

    # Content
    script: str = ""
    platform: Literal["youtube", "tiktok", "instagram", "shorts"] = "youtube"

    # Generated assets
    audio_path: str | None = None
    avatar_video_path: str | None = None
    music_path: str | None = None
    final_video_path: str | None = None
    thumbnail_path: str | None = None

    # Settings
    voice: str = "en-US-AriaNeural"
    avatar_image: str | None = None
    avatar_preset: str = "news_anchor"
    music_style: str = "corporate"
    music_duration: int = 30
    music_volume: float = 0.15

    # Aspect ratio based on platform
    aspect_ratio: str = field(default="16:9")

    # Project ID for database
    project_id: int | None = None

    def __post_init__(self):
        # Set aspect ratio based on platform
        if self.platform in ["tiktok", "shorts", "instagram"]:
            self.aspect_ratio = "9:16"
        else:
            self.aspect_ratio = "16:9"


class VideoProducer:
    """
    Complete Video Production Pipeline.

    Takes a script and produces a full video with:
    - AI-generated voiceover (Edge TTS)
    - Realistic talking head avatar (SadTalker)
    - Custom background music (MusicGen)
    - Professional video composition (MoviePy)

    Example:
        producer = VideoProducer()
        video = producer.produce(
            script="Welcome to our tech review...",
            avatar_image="presenter.jpg",
            platform="youtube"
        )
    """

    # Platform configurations
    PLATFORM_CONFIGS = {
        "youtube": {
            "aspect_ratio": "16:9",
            "resolution": (1920, 1080),
            "max_duration": 600,  # 10 min
        },
        "shorts": {
            "aspect_ratio": "9:16",
            "resolution": (1080, 1920),
            "max_duration": 60,
        },
        "tiktok": {
            "aspect_ratio": "9:16",
            "resolution": (1080, 1920),
            "max_duration": 180,  # 3 min
        },
        "instagram": {
            "aspect_ratio": "9:16",
            "resolution": (1080, 1920),
            "max_duration": 90,
        },
    }

    def __init__(self, output_dir: Path | None = None):
        """Initialize VideoProducer."""
        self.output_dir = output_dir or Path(config.PROCESSED_DIR) / "productions"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Lazy-loaded modules
        self._tts = None
        self._avatar = None
        self._composer = None
        self._processor = None
        self._brain = None
        self._db = None

        logger.info("🎬 VideoProducer initialized")

    @property
    def tts(self):
        """Lazy load TTS generator."""
        if self._tts is None:
            from .studio import GenerativeStudio

            self._tts = GenerativeStudio()
        return self._tts

    @property
    def avatar(self):
        """Lazy load avatar engine."""
        if self._avatar is None:
            from .avatar import AvatarEngine

            self._avatar = AvatarEngine(size=256, use_enhancer=False)
        return self._avatar

    @property
    def composer(self):
        """Lazy load music composer."""
        if self._composer is None:
            from .composer import MusicComposer

            self._composer = MusicComposer(model="small")
        return self._composer

    @property
    def processor(self):
        """Lazy load video processor."""
        if self._processor is None:
            from ..core.processor import VideoProcessor

            self._processor = VideoProcessor()
        return self._processor

    @property
    def brain(self):
        """Lazy load AI brain."""
        if self._brain is None:
            from .brain import HybridBrain

            self._brain = HybridBrain()
        return self._brain

    @property
    def db(self):
        """Lazy load database manager."""
        if self._db is None:
            self._db = DatabaseManager()
        return self._db

    def produce(
        self,
        script: str,
        avatar_image: str,
        name: str = "Untitled Video",
        platform: str = "youtube",
        voice: str = "en-US-AriaNeural",
        avatar_preset: str = "news_anchor",
        music_style: str | None = None,
        music_prompt: str | None = None,
        add_music: bool = True,
        save_project: bool = True,
        force_restart: bool = False,
    ) -> str | None:
        """
        Produce a complete video from script to final output.

        This method supports checkpoint-based resumability. If a previous
        production was interrupted, it will automatically resume from the
        last completed step.

        Args:
            script: The text script to convert to video.
            avatar_image: Path to the presenter/avatar face image.
            name: Project name.
            platform: Target platform (youtube, tiktok, shorts, instagram).
            voice: TTS voice to use.
            avatar_preset: Animation preset for avatar.
            music_style: Music style preset (if None, AI chooses based on script).
            music_prompt: Custom music prompt (overrides music_style).
            add_music: Whether to add background music.
            save_project: Whether to save project to database.
            force_restart: If True, ignore existing state and start fresh.

        Returns:
            Path to final video file.
        """
        start_time = time.time()

        # Create project
        project = VideoProject(
            name=name,
            script=script,
            platform=platform,  # type: ignore[arg-type]
            voice=voice,
            avatar_image=avatar_image,
            avatar_preset=avatar_preset,
            music_style=music_style or "corporate",
        )

        # Initialize manifest for checkpoint support
        project_dir = self.output_dir / name.replace(" ", "_")
        manifest = ProjectManifest(project_dir, project_name=name)

        # Check if we should resume or start fresh
        if force_restart:
            manifest.reset()
            logger.info(f"🔄 Force restart: '{name}'")
        elif manifest.get_resume_point():
            resume_step = manifest.get_resume_point()
            logger.info(
                f"♻️ Resuming production: '{name}' from {resume_step.value if resume_step else 'start'}"
            )

        # Save configuration for validation
        manifest.save_config(
            {
                "script": script[:100],  # First 100 chars for comparison
                "platform": platform,
                "voice": voice,
                "avatar_image": avatar_image,
            }
        )

        logger.info(f"🎬 Starting production: '{name}'")
        logger.info(f"   Platform: {platform}, Voice: {voice}")

        try:
            # Step 1: Generate voiceover (with checkpoint)
            if manifest.has_asset("audio"):
                project.audio_path = manifest.get_asset_path("audio")
                logger.info("⏭️ Step 1/4: Voiceover (cached)")
            else:
                logger.info("📢 Step 1/4: Generating voiceover...")
                manifest.set_current_step(ProductionStep.VOICEOVER)
                project.audio_path = self._generate_voiceover(project)
                if not project.audio_path:
                    manifest.mark_asset_failed("audio", "Voiceover generation failed")
                    manifest.save()
                    raise RuntimeError("Voiceover generation failed")
                manifest.register_asset("audio", project.audio_path)
                manifest.mark_step_complete(ProductionStep.VOICEOVER)

            # Step 2: Generate talking head avatar (with checkpoint)
            if manifest.has_asset("avatar_video"):
                project.avatar_video_path = manifest.get_asset_path("avatar_video")
                logger.info("⏭️ Step 2/4: Avatar video (cached)")
            else:
                logger.info("🎭 Step 2/4: Generating avatar video...")
                manifest.set_current_step(ProductionStep.AVATAR)
                project.avatar_video_path = self._generate_avatar(project)
                if not project.avatar_video_path:
                    manifest.mark_asset_failed(
                        "avatar_video", "Avatar generation failed"
                    )
                    manifest.save()
                    raise RuntimeError("Avatar generation failed")
                manifest.register_asset("avatar_video", project.avatar_video_path)
                manifest.mark_step_complete(ProductionStep.AVATAR)

            # Step 3: Generate background music (with checkpoint)
            if add_music:
                if manifest.has_asset("music"):
                    project.music_path = manifest.get_asset_path("music")
                    logger.info("⏭️ Step 3/4: Background music (cached)")
                else:
                    logger.info("🎵 Step 3/4: Composing background music...")
                    manifest.set_current_step(ProductionStep.MUSIC)
                    project.music_path = self._generate_music(project, music_prompt)
                    if project.music_path:
                        manifest.register_asset("music", project.music_path)
                    manifest.mark_step_complete(ProductionStep.MUSIC)
            else:
                logger.info("🎵 Step 3/4: Skipping music (disabled)")
                manifest.mark_step_complete(ProductionStep.MUSIC)

            # Step 4: Compose final video (with checkpoint)
            if manifest.has_asset("final_video"):
                project.final_video_path = manifest.get_asset_path("final_video")
                logger.info("⏭️ Step 4/4: Final video (cached)")
            else:
                logger.info("🎥 Step 4/4: Composing final video...")
                manifest.set_current_step(ProductionStep.COMPOSITION)
                project.final_video_path = self._compose_final(project)
                if not project.final_video_path:
                    manifest.mark_asset_failed("final_video", "Composition failed")
                    manifest.save()
                    raise RuntimeError("Video composition failed")
                manifest.register_asset("final_video", project.final_video_path)
                manifest.mark_step_complete(ProductionStep.COMPOSITION)

            # Save project to database
            if save_project:
                self._save_project(project)

            elapsed = time.time() - start_time
            logger.info(f"✅ Production complete in {elapsed:.1f}s")
            logger.info(f"   Output: {project.final_video_path}")
            logger.debug(f"   Manifest: {manifest.get_stats()}")

            return project.final_video_path

        except Exception as e:
            logger.error(f"❌ Production failed: {e}")
            manifest.save()  # Ensure state is saved for recovery
            return None

    def _generate_voiceover(self, project: VideoProject) -> str | None:
        """Generate TTS voiceover from script."""
        return self.tts.generate_voiceover(project.script, project.voice)

    def _generate_avatar(self, project: VideoProject) -> str | None:
        """Generate talking head avatar video."""
        if not project.avatar_image:
            logger.error("No avatar image provided")
            return None

        return self.avatar.generate(
            image_path=project.avatar_image,
            audio_path=project.audio_path,
            preset=project.avatar_preset,
        )

    def _generate_music(
        self, project: VideoProject, custom_prompt: str | None = None
    ) -> str | None:
        """Generate background music."""
        # Get audio duration
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(project.audio_path)
            duration = len(audio) // 1000  # Convert to seconds
        except Exception:
            duration = 30  # Default

        # Add buffer for music
        music_duration = min(duration + 5, 60)  # Cap at 60s for VRAM

        if custom_prompt:
            return self.composer.compose(custom_prompt, music_duration)
        else:
            # Use AI to generate appropriate music prompt
            try:
                music_prompt = self.brain.think(
                    f"""Generate a MusicGen prompt for background music.
Script theme: {project.script[:200]}...
Platform: {project.platform}
Return ONLY the music description (20 words max), no explanation.
""",
                    context="You are a music director.",
                )
            except Exception:
                music_prompt = f"{project.music_style} background music"

            return self.composer.compose(music_prompt, music_duration)

    def _compose_final(self, project: VideoProject) -> str | None:
        """Compose final video with all assets."""
        try:
            from moviepy import (
                AudioFileClip,
                CompositeAudioClip,
                VideoFileClip,
            )
            from moviepy.audio.fx import MultiplyVolume

            # Load avatar video
            video = VideoFileClip(project.avatar_video_path)

            # Prepare audio tracks
            audio_tracks = [video.audio]  # Original speech

            # Add background music if available
            if project.music_path and Path(project.music_path).exists():
                music = AudioFileClip(project.music_path)

                # Loop music if shorter than video
                if music.duration < video.duration:
                    loops_needed = int(video.duration / music.duration) + 1
                    from moviepy import concatenate_audioclips

                    music = concatenate_audioclips([music] * loops_needed)

                # Trim to video length and reduce volume
                music = music.subclipped(0, video.duration)
                music = music.with_effects([MultiplyVolume(project.music_volume)])

                audio_tracks.append(music)

            # Composite audio
            final_audio = CompositeAudioClip(audio_tracks)
            video = video.with_audio(final_audio)

            # Handle aspect ratio for platform
            config = self.PLATFORM_CONFIGS.get(
                project.platform, self.PLATFORM_CONFIGS["youtube"]
            )
            target_res = config["resolution"]

            # Resize if needed (for vertical videos)
            if project.aspect_ratio == "9:16" and video.w > video.h:
                # Convert horizontal to vertical with padding
                from moviepy import ColorClip, CompositeVideoClip

                # Scale to fit width
                scale = target_res[0] / video.w
                video = video.resized(scale)

                # Create background
                bg = ColorClip(target_res, color=(0, 0, 0), duration=video.duration)

                # Center video vertically
                video = video.with_position(("center", "center"))
                video = CompositeVideoClip([bg, video])

            # Output path
            output_path = (
                self.output_dir
                / f"{project.name.replace(' ', '_')}_{int(time.time())}.mp4"
            )

            # Write final video
            video.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )

            # Cleanup
            video.close()

            return str(output_path)

        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            return None

    def _save_project(self, project: VideoProject) -> int | None:
        """Save project to database."""
        try:
            project_id = self.db.create_project(
                name=project.name,
                description=project.description,
                platform=project.platform,
                aspect_ratio=project.aspect_ratio,
            )

            self.db.save_project_draft(
                project_id,
                script=project.script,
                audio_paths=[project.audio_path] if project.audio_path else [],
                video_paths=[
                    p
                    for p in [project.avatar_video_path, project.final_video_path]
                    if p
                ],
                settings={
                    "voice": project.voice,
                    "avatar_image": project.avatar_image,
                    "avatar_preset": project.avatar_preset,
                    "music_style": project.music_style,
                },
            )

            project.project_id = project_id
            logger.info(f"📁 Project saved (ID: {project_id})")
            return project_id

        except Exception as e:
            logger.warning(f"Failed to save project: {e}")
            return None

    def produce_news_segment(
        self,
        headline: str,
        body: str,
        anchor_image: str,
        music: bool = True,
    ) -> str | None:
        """
        Produce a news segment video.

        Args:
            headline: News headline.
            body: News body text.
            anchor_image: Path to news anchor face image.
            music: Add background music.

        Returns:
            Path to news video.
        """
        script = f"{headline}. {body}"
        return self.produce(
            script=script,
            avatar_image=anchor_image,
            name=f"News_{headline[:30]}",
            platform="youtube",
            voice="en-US-AriaNeural",
            avatar_preset="news_anchor",
            music_style="news",
            add_music=music,
        )

    def produce_short(
        self,
        script: str,
        avatar_image: str,
        platform: str = "tiktok",
        voice: str = "en-US-JennyNeural",
    ) -> str | None:
        """
        Produce a vertical short-form video.

        Args:
            script: Short-form script (keep under 60s when spoken).
            avatar_image: Path to avatar face image.
            platform: Target platform (tiktok, shorts, instagram).
            voice: TTS voice.

        Returns:
            Path to short video.
        """
        return self.produce(
            script=script,
            avatar_image=avatar_image,
            name=f"Short_{int(time.time())}",
            platform=platform,
            voice=voice,
            avatar_preset="energetic",
            music_style="gaming",
            add_music=True,
        )

    def produce_tutorial(
        self,
        script: str,
        presenter_image: str,
        topic: str = "Tutorial",
    ) -> str | None:
        """
        Produce a tutorial/educational video.

        Args:
            script: Tutorial script.
            presenter_image: Path to presenter face image.
            topic: Tutorial topic for naming.

        Returns:
            Path to tutorial video.
        """
        return self.produce(
            script=script,
            avatar_image=presenter_image,
            name=f"Tutorial_{topic}",
            platform="youtube",
            voice="en-US-GuyNeural",
            avatar_preset="presentation",
            music_style="tutorial",
            add_music=True,
        )

    def batch_produce(
        self,
        projects: list[dict],
    ) -> list[str]:
        """
        Produce multiple videos in batch.

        Args:
            projects: List of project configurations.

        Returns:
            List of output video paths.
        """
        results = []
        for i, proj in enumerate(projects):
            logger.info(
                f"🎬 Batch {i + 1}/{len(projects)}: {proj.get('name', 'Untitled')}"
            )
            result = self.produce(**proj)
            if result:
                results.append(result)
        return results


# Convenience function
def produce_video(
    script: str,
    avatar_image: str,
    platform: str = "youtube",
    **kwargs,
) -> str | None:
    """
    Quick function to produce a complete video.

    Args:
        script: Video script text.
        avatar_image: Path to avatar/presenter image.
        platform: Target platform.
        **kwargs: Additional options.

    Returns:
        Path to produced video.
    """
    producer = VideoProducer()
    return producer.produce(script, avatar_image, platform=platform, **kwargs)
