"""
Realistic Avatar Engine using SadTalker.

Generates talking head videos from a single image and audio.
Creates realistic lip-sync and facial animations.

Optimized for RTX 2060 (6GB VRAM) using 256px face model.
"""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

import torch
from loguru import logger

from ..config import config

# Check for SadTalker availability
SADTALKER_AVAILABLE = False
SADTALKER_PATH = None


def _find_sadtalker() -> Path | None:
    """Find SadTalker installation path."""
    possible_paths = [
        Path.home() / "SadTalker",
        Path.home() / ".local" / "SadTalker",
        Path("/opt/SadTalker"),
        Path.cwd() / "SadTalker",
    ]

    for path in possible_paths:
        if (path / "inference.py").exists():
            return path
    return None


class AvatarEngine:
    """
    Realistic Talking Head Avatar Generator using SadTalker.

    Creates lip-synced videos from:
    - A single face image (photo, AI-generated, illustration)
    - Audio file (speech, narration)

    Features:
    - Realistic lip movements
    - Natural head motion
    - Expression generation
    - Multiple presets for different use cases

    Optimized for RTX 2060:
    - Uses 256px face model by default
    - Disables enhancer to save VRAM
    - Half-precision (FP16) inference
    """

    # Preset configurations
    PRESETS = {
        "news_anchor": {
            "still": False,
            "expression_scale": 1.0,
            "pose_style": 0,  # Natural head movement
            "description": "Professional news anchor with subtle movements",
        },
        "presentation": {
            "still": True,
            "expression_scale": 0.8,
            "pose_style": 0,
            "description": "Minimal movement, ideal for presentations",
        },
        "energetic": {
            "still": False,
            "expression_scale": 1.5,
            "pose_style": 1,
            "description": "More expressive, dynamic movements",
        },
        "subtle": {
            "still": True,
            "expression_scale": 0.5,
            "pose_style": 0,
            "description": "Very subtle, professional look",
        },
        "realistic": {
            "still": False,
            "expression_scale": 1.2,
            "pose_style": 2,
            "description": "Most realistic natural movements",
        },
    }

    def __init__(
        self,
        size: Literal[256, 512] = 256,
        use_enhancer: bool = False,
        device: str | None = None,
    ) -> None:
        """
        Initialize AvatarEngine.

        Args:
            size: Face crop size (256 recommended for 6GB VRAM).
            use_enhancer: Use GFPGAN face enhancement (requires more VRAM).
            device: Device to run on. Auto-detects if None.
        """
        self.size = size
        self.use_enhancer = use_enhancer
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.output_dir = Path(config.PROCESSED_DIR) / "avatars"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Find SadTalker installation
        self.sadtalker_path = _find_sadtalker()

        if self.sadtalker_path:
            logger.info(f"✅ SadTalker found at: {self.sadtalker_path}")
        else:
            logger.warning("⚠️ SadTalker not installed. Using HuggingFace API fallback.")

        logger.info(
            f"🎭 AvatarEngine initialized (size: {size}px, device: {self.device})"
        )

    def generate(
        self,
        image_path: str,
        audio_path: str,
        output_path: str | None = None,
        preset: str = "news_anchor",
        still: bool | None = None,
        expression_scale: float | None = None,
    ) -> str | None:
        """
        Generate a talking head video.

        Args:
            image_path: Path to face image (any person/avatar photo).
            audio_path: Path to audio file (speech to lip-sync).
            output_path: Optional output video path.
            preset: Animation preset name.
            still: Override preset - if True, reduces head movement.
            expression_scale: Override preset - controls expression intensity.

        Returns:
            Path to generated video file.
        """
        image_path = Path(image_path)
        audio_path = Path(audio_path)

        if not image_path.exists():
            logger.error(f"❌ Image not found: {image_path}")
            return None

        if not audio_path.exists():
            logger.error(f"❌ Audio not found: {audio_path}")
            return None

        # Get preset settings
        preset_config = self.PRESETS.get(preset, self.PRESETS["news_anchor"])

        # Allow overrides
        _still = still if still is not None else preset_config["still"]
        _expression = (
            expression_scale
            if expression_scale is not None
            else preset_config["expression_scale"]
        )

        logger.info(f"🎭 Generating avatar: {image_path.name} + {audio_path.name}")
        logger.info(f"   Preset: {preset}, Still: {_still}, Expression: {_expression}")

        # Try local SadTalker first, fallback to API
        if self.sadtalker_path:
            return self._generate_local(
                image_path,
                audio_path,
                output_path,
                still=_still,
                expression_scale=_expression,
                pose_style=preset_config["pose_style"],
            )
        else:
            return self._generate_api(image_path, audio_path, output_path)

    def _generate_local(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: str | None,
        still: bool,
        expression_scale: float,
        pose_style: int,
    ) -> str | None:
        """Generate using local SadTalker installation."""
        try:
            start_time = time.time()

            # Build command
            cmd = [
                "python",
                str(self.sadtalker_path / "inference.py"),
                "--source_image",
                str(image_path),
                "--driven_audio",
                str(audio_path),
                "--result_dir",
                str(self.output_dir),
                "--size",
                str(self.size),
                "--expression_scale",
                str(expression_scale),
                "--pose_style",
                str(pose_style),
            ]

            if still:
                cmd.append("--still")

            if not self.use_enhancer:
                cmd.extend(["--enhancer", "none"])

            if self.device == "cpu":
                cmd.append("--cpu")

            # Run SadTalker
            logger.info("🔄 Running SadTalker inference...")
            result = subprocess.run(
                cmd,
                cwd=self.sadtalker_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"❌ SadTalker failed: {result.stderr}")
                return None

            # Find output file (SadTalker creates timestamped folders)
            output_files = list(self.output_dir.glob("**/result*.mp4"))
            if not output_files:
                output_files = list(self.output_dir.glob("**/*.mp4"))

            if not output_files:
                logger.error("❌ No output video found")
                return None

            # Get most recent output
            latest = max(output_files, key=lambda p: p.stat().st_mtime)

            # Move to desired location
            if output_path:
                final_path = Path(output_path)
            else:
                final_path = self.output_dir / f"avatar_{int(time.time())}.mp4"

            shutil.move(str(latest), str(final_path))

            elapsed = time.time() - start_time
            logger.info(f"✅ Avatar generated in {elapsed:.1f}s → {final_path.name}")

            return str(final_path)

        except subprocess.TimeoutExpired:
            logger.error("❌ SadTalker timed out")
            return None
        except Exception as e:
            logger.error(f"❌ Avatar generation failed: {e}")
            return None

    def _generate_api(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: str | None,
    ) -> str | None:
        """Generate using HuggingFace Spaces API (fallback)."""
        try:
            if not config.HF_TOKEN:
                logger.error("❌ HF_TOKEN required for API fallback")
                return None

            logger.info("🔄 Using HuggingFace API (SadTalker not installed locally)")
            start_time = time.time()

            # Use gradio_client for Spaces
            try:
                from gradio_client import Client, handle_file

                client = Client("vinthony/SadTalker")

                result = client.predict(
                    source_image=handle_file(str(image_path)),
                    driven_audio=handle_file(str(audio_path)),
                    api_name="/predict",
                )

                # Result is a file path
                if result and Path(result).exists():
                    if output_path:
                        final_path = Path(output_path)
                    else:
                        final_path = self.output_dir / f"avatar_{int(time.time())}.mp4"

                    shutil.copy(result, str(final_path))

                    elapsed = time.time() - start_time
                    logger.info(f"✅ Avatar generated via API in {elapsed:.1f}s")
                    return str(final_path)

            except ImportError:
                logger.error(
                    "❌ gradio_client not installed. Run: pip install gradio_client"
                )
                return None

        except Exception as e:
            logger.error(f"❌ API generation failed: {e}")
            return None

    def generate_news_anchor(
        self,
        anchor_image: str,
        script: str,
        tts_voice: str = "en-US-AriaNeural",
    ) -> str | None:
        """
        Generate a news anchor video from script text.

        This is a high-level method that:
        1. Converts script to speech using Edge TTS
        2. Generates lip-synced avatar video

        Args:
            anchor_image: Path to anchor's face image.
            script: The news script to speak.
            tts_voice: Voice for text-to-speech.

        Returns:
            Path to generated news video.
        """
        try:
            # Generate TTS audio
            from .studio import GenerativeStudio

            studio = GenerativeStudio()
            audio_path = studio.generate_voiceover(script, tts_voice)

            if not audio_path:
                logger.error("❌ TTS generation failed")
                return None

            # Generate avatar video
            return self.generate(anchor_image, audio_path, preset="news_anchor")

        except Exception as e:
            logger.error(f"❌ News anchor generation failed: {e}")
            return None

    def generate_presenter(
        self,
        presenter_image: str,
        audio_or_script: str,
        is_script: bool = False,
        voice: str = "en-US-GuyNeural",
    ) -> str | None:
        """
        Generate a presentation-style avatar video.

        Args:
            presenter_image: Path to presenter's image.
            audio_or_script: Either audio file path or script text.
            is_script: If True, audio_or_script is text to convert to speech.
            voice: TTS voice if is_script is True.

        Returns:
            Path to generated video.
        """
        audio_path = audio_or_script

        if is_script:
            from .studio import GenerativeStudio

            studio = GenerativeStudio()
            audio_path = studio.generate_voiceover(audio_or_script, voice)
            if not audio_path:
                return None

        return self.generate(presenter_image, audio_path, preset="presentation")

    def batch_generate(
        self,
        jobs: list[dict],
    ) -> list[str]:
        """
        Generate multiple avatar videos.

        Args:
            jobs: List of dicts with 'image', 'audio', and optional 'preset'.

        Returns:
            List of output video paths.
        """
        results = []
        for i, job in enumerate(jobs):
            logger.info(f"🎭 Processing job {i + 1}/{len(jobs)}")
            result = self.generate(
                job["image"], job["audio"], preset=job.get("preset", "news_anchor")
            )
            if result:
                results.append(result)
        return results

    def get_presets(self) -> dict[str, dict]:
        """Get available animation presets."""
        return {
            k: {"description": v["description"], **v} for k, v in self.PRESETS.items()
        }

    @staticmethod
    def install_sadtalker() -> str:
        """Return installation instructions for SadTalker."""
        return """
# SadTalker Installation Guide

## Clone Repository
```bash
cd ~
git clone https://github.com/OpenTalker/SadTalker
cd SadTalker

# Create environment
conda create -n sadtalker python=3.10
conda activate sadtalker

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Download models (~2GB)
bash scripts/download_models.sh
```

## Verify Installation
```bash
python inference.py \\
    --source_image examples/source_image/full_body_1.png \\
    --driven_audio examples/driven_audio/bus_chinese.wav \\
    --size 256
```
"""


# Convenience function
def create_talking_head(
    image_path: str,
    audio_path: str,
    preset: str = "news_anchor",
) -> str | None:
    """
    Quick function to create a talking head video.

    Args:
        image_path: Path to face image.
        audio_path: Path to audio file.
        preset: Animation preset.

    Returns:
        Path to generated video.
    """
    engine = AvatarEngine(size=256, use_enhancer=False)
    return engine.generate(image_path, audio_path, preset=preset)


def create_news_anchor(
    image_path: str,
    script: str,
    voice: str = "en-US-AriaNeural",
) -> str | None:
    """
    Quick function to create a news anchor video.

    Args:
        image_path: Path to anchor's image.
        script: News script text.
        voice: TTS voice.

    Returns:
        Path to generated video.
    """
    engine = AvatarEngine(size=256, use_enhancer=False)
    return engine.generate_news_anchor(image_path, script, voice)
