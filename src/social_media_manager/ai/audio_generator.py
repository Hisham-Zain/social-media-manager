import logging
from pathlib import Path
from typing import Any

from ..config import config

logger = logging.getLogger(__name__)

# Import VoxCPM engine
try:
    from .voxcpm_engine import VoxCPMEngine

    VOXCPM_AVAILABLE = True
except ImportError:
    VOXCPM_AVAILABLE = False
    VoxCPMEngine = None  # type: ignore


class TTSGenerator:
    """
    Local Text-to-Speech using VoxCPM.

    Attributes:
        output_dir (Path): Directory where generated audio files are saved.
        available (bool): Whether VoxCPM is available.
    """

    def __init__(self) -> None:
        """
        Initialize the TTSGenerator.

        Attempts to initialize VoxCPM. If unavailable, disables audio generation.
        """
        self.output_dir: Path = config.GENERATED_DIR
        self._engine: Any = None
        self.available: bool = False

        if VOXCPM_AVAILABLE:
            try:
                self._engine = VoxCPMEngine(output_dir=self.output_dir)
                self.available = self._engine.available
            except Exception as e:
                logger.warning(f"VoxCPM initialization failed: {e}")

    def generate_audio(
        self,
        text: str,
        filename: str = "audio.wav",
        voice: str | None = None,
    ) -> str | None:
        """
        Generate audio from text using VoxCPM.

        Args:
            text: The text to convert to speech.
            filename: The output filename. Defaults to "audio.wav".
            voice: Voice name or reference audio path.

        Returns:
            Path to the generated audio file, or None if generation failed.
        """
        if not self.available or self._engine is None:
            return None

        try:
            output_path = self.output_dir / filename
            return self._engine.generate(
                text=text,
                voice=voice,
                output_path=output_path,
            )
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return None


# Backwards compatibility alias
ChatterboxGenerator = TTSGenerator
