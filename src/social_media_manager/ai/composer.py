"""
AI Music Composer using AudioCraft (MusicGen).

Generates custom music tracks from text prompts.
Optimized for RTX 2060 (6GB VRAM) using musicgen-small.
"""

import time
from pathlib import Path
from typing import Literal

import torch
from loguru import logger

from ..config import config

# Lazy imports for heavy models
MUSICGEN_AVAILABLE = False


class MusicComposer:
    """
    AI Music Composer using Meta's MusicGen.

    Generates royalty-free music from text descriptions.
    Perfect for creating custom soundtracks for videos.

    Models:
    - small: 300M params, ~5GB VRAM (RTX 2060 friendly)
    - medium: 1.5B params, ~10GB VRAM
    - melody: 1.5B params, can condition on melody
    """

    MODELS = {
        "small": "facebook/musicgen-small",
        "medium": "facebook/musicgen-medium",
        "melody": "facebook/musicgen-melody",
    }

    # Music style presets for quick generation
    STYLE_PRESETS = {
        "tech_review": "upbeat electronic music with synthesizers and modern beats",
        "tutorial": "calm ambient background music, soft and professional",
        "gaming": "intense electronic music with heavy bass and fast tempo",
        "vlog": "happy acoustic guitar music, warm and friendly",
        "news": "serious orchestral news broadcast music",
        "workout": "high energy EDM with driving beats and drops",
        "relaxation": "peaceful piano and nature sounds, meditation music",
        "cinematic": "epic orchestral soundtrack with drums and strings",
        "comedy": "playful quirky music with funny sound effects",
        "corporate": "professional uplifting corporate background music",
    }

    def __init__(
        self,
        model: Literal["small", "medium", "melody"] = "small",
        device: str | None = None,
    ) -> None:
        """
        Initialize MusicComposer.

        Args:
            model: Model size. Use "small" for RTX 2060 (6GB VRAM).
            device: Device to run on. Auto-detects if None.
        """
        self.model_name = self.MODELS.get(model, self.MODELS["small"])
        self.model_size = model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.processor = None

        self.output_dir = (
            Path(config.MUSIC_DIR)
            if hasattr(config, "MUSIC_DIR")
            else Path.home() / ".social_media_manager" / "music" / "generated"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"🎵 MusicComposer initialized (model: {model}, device: {self.device})"
        )

    def _load_model(self) -> bool:
        """Lazy load the MusicGen model."""
        if self.model is not None:
            return True

        try:
            from transformers import AutoProcessor, MusicgenForConditionalGeneration

            logger.info(f"🔄 Loading MusicGen model: {self.model_name}")

            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = MusicgenForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )
            self.model = self.model.to(self.device)

            logger.info("✅ MusicGen model loaded successfully")
            return True

        except ImportError:
            logger.error("❌ Transformers not installed. Run: pip install transformers")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load MusicGen: {e}")
            return False

    def compose(
        self,
        prompt: str,
        duration_seconds: int = 10,
        guidance_scale: float = 3.0,
        output_path: str | None = None,
    ) -> str | None:
        """
        Compose music from a text prompt.

        Args:
            prompt: Description of the music to generate.
                   Example: "upbeat electronic dance music with heavy bass"
            duration_seconds: Length of audio to generate (max 30s for 6GB VRAM).
            guidance_scale: How closely to follow the prompt (higher = more accurate).
            output_path: Optional output file path.

        Returns:
            Path to generated audio file (WAV format).
        """
        if not self._load_model():
            return None

        try:
            logger.info(f"🎵 Composing: '{prompt[:50]}...' ({duration_seconds}s)")
            start_time = time.time()

            # Tokenize prompt
            inputs = self.processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            # Calculate max tokens based on duration
            # MusicGen generates ~50 tokens per second at 32kHz
            max_tokens = min(duration_seconds * 50, 1500)  # Cap for VRAM safety

            # Generate audio
            with torch.no_grad():
                audio_values = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    guidance_scale=guidance_scale,
                    do_sample=True,
                )

            # Get sample rate from model config
            sample_rate = self.model.config.audio_encoder.sampling_rate

            # Convert to numpy and save
            audio_data = audio_values[0, 0].cpu().numpy()

            # Determine output path
            if output_path is None:
                safe_prompt = (
                    "".join(c for c in prompt[:30] if c.isalnum() or c == " ")
                    .strip()
                    .replace(" ", "_")
                )
                output_path = (
                    self.output_dir / f"music_{safe_prompt}_{int(time.time())}.wav"
                )
            else:
                output_path = Path(output_path)

            # Save as WAV
            import scipy.io.wavfile as wav

            wav.write(str(output_path), sample_rate, audio_data)

            elapsed = time.time() - start_time
            logger.info(f"✅ Music composed in {elapsed:.1f}s → {output_path.name}")

            # Free VRAM
            torch.cuda.empty_cache()

            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Music composition failed: {e}")
            torch.cuda.empty_cache()
            return None

    def compose_with_style(
        self,
        style: str,
        duration_seconds: int = 10,
        **kwargs,
    ) -> str | None:
        """
        Compose music using a preset style.

        Args:
            style: Style preset name (tech_review, tutorial, gaming, etc.)
            duration_seconds: Length of audio to generate.

        Available styles:
            - tech_review: Upbeat electronic
            - tutorial: Calm ambient
            - gaming: Intense electronic
            - vlog: Happy acoustic
            - news: Serious orchestral
            - workout: High energy EDM
            - relaxation: Peaceful piano
            - cinematic: Epic orchestral
            - comedy: Playful quirky
            - corporate: Professional uplifting

        Returns:
            Path to generated audio file.
        """
        prompt = self.STYLE_PRESETS.get(style, style)
        return self.compose(prompt, duration_seconds, **kwargs)

    def compose_for_video(
        self,
        video_description: str,
        mood: str = "neutral",
        duration_seconds: int = 30,
        brain=None,
    ) -> str | None:
        """
        Compose music tailored for a video using AI to generate the prompt.

        Args:
            video_description: Description of the video content.
            mood: Desired mood (upbeat, calm, intense, etc.)
            duration_seconds: Length of music needed.
            brain: Optional HybridBrain instance for prompt generation.

        Returns:
            Path to generated audio file.
        """
        # Generate optimized music prompt using AI
        if brain:
            try:
                prompt = brain.think(
                    f"""Create a MusicGen prompt for background music.
Video: {video_description}
Mood: {mood}
Return ONLY the music description, no explanation.
Example: "upbeat electronic music with synthesizers and driving beats"
""",
                    context="You are a music director creating soundtracks for videos.",
                )
            except Exception as e:
                logger.warning(f"AI prompt generation failed, using fallback: {e}")
                prompt = f"{mood} background music suitable for {video_description}"
        else:
            prompt = f"{mood} background music suitable for {video_description}"

        return self.compose(prompt, duration_seconds)

    def batch_compose(
        self,
        prompts: list[str],
        duration_seconds: int = 10,
    ) -> list[str]:
        """
        Compose multiple tracks.

        Args:
            prompts: List of music descriptions.
            duration_seconds: Length for each track.

        Returns:
            List of paths to generated audio files.
        """
        results = []
        for i, prompt in enumerate(prompts):
            logger.info(f"🎵 Composing track {i + 1}/{len(prompts)}")
            path = self.compose(prompt, duration_seconds)
            if path:
                results.append(path)
        return results

    def get_available_styles(self) -> dict[str, str]:
        """Get dictionary of available style presets."""
        return self.STYLE_PRESETS.copy()

    def unload(self) -> None:
        """Unload model to free VRAM."""
        if self.model is not None:
            del self.model
            del self.processor
            self.model = None
            self.processor = None
            torch.cuda.empty_cache()
            logger.info("🧹 MusicComposer model unloaded")


# Convenience function
def compose_music(prompt: str, duration: int = 10) -> str | None:
    """
    Quick function to compose music from a prompt.

    Args:
        prompt: Description of the music.
        duration: Length in seconds.

    Returns:
        Path to generated audio file.
    """
    composer = MusicComposer(model="small")
    return composer.compose(prompt, duration)


def compose_for_style(style: str, duration: int = 10) -> str | None:
    """
    Quick function to compose music from a style preset.

    Args:
        style: Style preset name.
        duration: Length in seconds.

    Returns:
        Path to generated audio file.
    """
    composer = MusicComposer(model="small")
    return composer.compose_with_style(style, duration)
