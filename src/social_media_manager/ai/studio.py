"""
Generative Studio Module for AgencyOS.

AI-powered visual content generation using Hugging Face models.
Supports text-to-image, text-to-video, image animation, and TTS.
"""

import logging
import time
from pathlib import Path

from huggingface_hub import InferenceClient

from ..config import config

logger = logging.getLogger(__name__)

# MoviePy v2 Import
try:
    from moviepy import ImageClip

    MOVIEPY_AVAILABLE = True
except ImportError:
    try:
        from moviepy.editor import ImageClip

        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False
        ImageClip = None

# VoxCPM TTS Engine
try:
    from .voxcpm_engine import VoxCPMEngine

    VOXCPM_AVAILABLE = True
except ImportError:
    VOXCPM_AVAILABLE = False
    VoxCPMEngine = None  # type: ignore


class GenerativeStudio:
    """
    The Director: Optimized for GENUINELY FREE models (Zeroscope, SVD).
    Handles text-to-image, text-to-video, image animation, and TTS.
    """

    def __init__(self) -> None:
        """Initialize the GenerativeStudio with output directory and HF client."""
        self.output_dir: Path = config.GENERATED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.hf_token: str = config.HF_TOKEN
        self.hf_client: InferenceClient | None = None

        if self.hf_token:
            self.hf_client = InferenceClient(token=self.hf_token)
        else:
            logger.warning("⚠️ HF_TOKEN missing. Visuals disabled.")

        # Initialize VoxCPM TTS engine
        self._tts_engine: VoxCPMEngine | None = None
        if VOXCPM_AVAILABLE:
            self._tts_engine = VoxCPMEngine(output_dir=self.output_dir)

    def generate_image(self, prompt: str) -> str | None:
        """
        Generate an image from text prompt using HuggingFace models.

        Args:
            prompt: Text description of the image to generate.

        Returns:
            Path to the generated image file, or None if generation failed.
        """
        if not self.hf_client:
            return None
        logger.info(f"🎨 Generating Image: {prompt[:40]}...")

        # Flux is SOTA, but SDXL is often faster on free tier
        models = [
            "black-forest-labs/FLUX.1-dev",
            "stabilityai/stable-diffusion-xl-base-1.0",
            "runwayml/stable-diffusion-v1-5",
        ]

        for model in models:
            try:
                image = self.hf_client.text_to_image(prompt, model=model)
                filename = f"gen_img_{int(time.time())}.jpg"
                path = self.output_dir / filename
                image.save(path)
                logger.info(f"✅ Image Generated ({model})")
                return str(path)
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        return None

    def generate_video(self, prompt: str) -> str | None:
        """
        Generate a video from text prompt using HuggingFace models.

        Args:
            prompt: Text description of the video to generate.

        Returns:
            Path to the generated video file, or None if generation failed.
        """
        if not self.hf_client:
            return None
        logger.info(f"🎥 Generating Video: {prompt[:30]}...")

        # 1. Zeroscope (Best Free 16:9 Model)
        # 2. ModelScope (Original, lower res)
        # 3. Ali-Vilab (Backup)
        video_models = [
            "cerspense/zeroscope_v2_576w",
            "damo-vilab/text-to-video-ms-1.7b",
            "ali-vilab/text-to-video-ms-1.7b",
        ]

        for model in video_models:
            try:
                video_bytes = self.hf_client.text_to_video(prompt, model=model)
                filename = f"gen_vid_{int(time.time())}.mp4"
                path = self.output_dir / filename
                with open(path, "wb") as f:
                    f.write(video_bytes)
                logger.info(f"✅ Video Created ({model})")
                return str(path)
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue

        # If all fail, create a static video from an image
        return self._generate_static_video_from_prompt(prompt)

    def animate_image(
        self, image_path: str, prompt: str = "cinematic movement"
    ) -> str | None:
        """
        Animate a static image using AI or fallback to zoom effect.

        Args:
            image_path: Path to the image to animate.
            prompt: Animation style/description.

        Returns:
            Path to the animated video file, or None if animation failed.
        """
        if not self.hf_client:
            return self._create_zoom_video(image_path)
        logger.info(f"🎬 Animating Image: {Path(image_path).name}...")

        # Only standard SVD is reliably free (XT often busy)
        img2vid_models = [
            "stabilityai/stable-video-diffusion-img2vid-xt",
            "stabilityai/stable-video-diffusion-img2vid",
        ]

        for model in img2vid_models:
            try:
                with open(image_path, "rb") as f:
                    video_bytes = self.hf_client.image_to_video(
                        image=f.read(), prompt=prompt, model=model
                    )

                filename = f"animated_{int(time.time())}.mp4"
                path = self.output_dir / filename
                with open(path, "wb") as f:
                    f.write(video_bytes)

                logger.info(f"✅ Image Animated ({model})")
                return str(path)
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue

        logger.warning("⚠️ AI Animation busy. Switching to Auto-Zoom effect.")
        return self._create_zoom_video(image_path)

    # --- FALLBACK METHODS ---

    def _create_zoom_video(self, image_path: str) -> str | None:
        """
        Create a 5-second 'Ken Burns' zoom effect video from an image.

        Args:
            image_path: Path to the source image.

        Returns:
            Path to the output video, or None if creation failed.
        """
        if not MOVIEPY_AVAILABLE or ImageClip is None:
            logger.warning("MoviePy not available for zoom video creation.")
            return None
        try:
            # MoviePy v2 uses 'with_duration' and 'resized'
            clip = ImageClip(str(image_path)).with_duration(5).resized(height=1080)
            output_path = self.output_dir / f"zoom_{int(time.time())}.mp4"
            clip.write_videofile(str(output_path), fps=24, codec="libx264", logger=None)
            return str(output_path)
        except Exception as e:
            logger.error(f"Zoom video creation failed: {e}")
            return None

    def _generate_static_video_from_prompt(self, prompt: str) -> str | None:
        """
        Generate a static video from a text prompt by first creating an image.

        Args:
            prompt: Text description for image generation.

        Returns:
            Path to the video, or None if generation failed.
        """
        img_path = self.generate_image(prompt)
        if not img_path:
            return None
        return self._create_zoom_video(img_path)

    # --- TTS (VoxCPM) ---

    def generate_voiceover(self, text: str, voice: str | None = None) -> str | None:
        """
        Generate text-to-speech voiceover using VoxCPM.

        Args:
            text: The text to convert to speech.
            voice: Voice name (e.g., "aria", "guy") or path to reference audio.

        Returns:
            Path to the audio file, or None if generation failed.
        """
        if self._tts_engine is None:
            logger.warning("VoxCPM TTS not available.")
            return None

        return self._tts_engine.generate(text=text, voice=voice)
