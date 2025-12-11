"""
Voice Cloning for AgencyOS using VoxCPM.

Zero-shot voice cloning using VoxCPM's native capabilities.
Simply provide a reference audio file (~10 seconds) and text to clone.

Pipeline: Text + Reference Audio → VoxCPM → Cloned Voice Audio
"""

import hashlib
import logging
from pathlib import Path

from ..config import config

logger = logging.getLogger(__name__)

# Import VoxCPM engine
try:
    from .voxcpm_engine import VoxCPMEngine

    VOXCPM_AVAILABLE = True
except ImportError:
    VOXCPM_AVAILABLE = False
    VoxCPMEngine = None  # type: ignore


class VoiceCloner:
    """
    Zero-shot voice cloning using VoxCPM.

    Simply provide a reference audio and text - no training required.

    Example:
        cloner = VoiceCloner()

        # Clone voice from a reference audio
        audio_path = cloner.clone(
            text="Hello, this is my cloned voice!",
            reference_audio="/path/to/reference.wav"
        )
    """

    def __init__(
        self,
        output_dir: Path | None = None,
    ):
        """
        Initialize Voice Cloner.

        Args:
            output_dir: Directory for output audio files.
        """
        self.output_dir = output_dir or config.PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._engine: VoxCPMEngine | None = None
        if VOXCPM_AVAILABLE:
            self._engine = VoxCPMEngine(output_dir=self.output_dir)

        logger.info(f"🎤 Voice Cloner initialized (VoxCPM: {self.available})")

    @property
    def available(self) -> bool:
        """Check if voice cloning is available."""
        return self._engine is not None and self._engine.available

    def clone(
        self,
        text: str,
        reference_audio: str | Path,
        output_path: str | Path | None = None,
    ) -> str | None:
        """
        Clone voice from reference audio.

        Args:
            text: Text to speak with cloned voice.
            reference_audio: Path to reference audio (10 seconds ideal).
            output_path: Optional output path.

        Returns:
            Path to the generated audio file, or None if failed.
        """
        if not self.available or self._engine is None:
            logger.error("Voice cloning not available")
            return None

        ref_path = Path(reference_audio)
        if not ref_path.exists():
            logger.error(f"Reference audio not found: {reference_audio}")
            return None

        # Generate output filename
        if output_path is None:
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            filename = f"clone_{text_hash}.wav"
            output_path = self.output_dir / filename

        return self._engine.clone_voice(
            text=text,
            reference_audio=str(ref_path),
            output_path=output_path,
        )

    def clone_with_voice(
        self,
        text: str,
        voice: str,
    ) -> str | None:
        """
        Clone using a named voice from the voices library.

        Args:
            text: Text to speak.
            voice: Voice name (e.g., "aria", "guy").

        Returns:
            Path to the generated audio file, or None if failed.
        """
        if not self.available or self._engine is None:
            logger.error("Voice cloning not available")
            return None

        return self._engine.generate(text=text, voice=voice)

    def list_voices(self) -> list[str]:
        """List available named voices."""
        if self._engine is None:
            return []
        return self._engine.list_voices()


# Convenience function
def clone_voice(text: str, reference_audio: str) -> str | None:
    """Quick function to clone text with a reference voice."""
    cloner = VoiceCloner()
    return cloner.clone(text, reference_audio)
