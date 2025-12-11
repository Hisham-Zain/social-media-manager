"""
Content Dubber using VoxCPM for AgencyOS.

Generates dubbed audio in target languages using VoxCPM's neural TTS.
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


class ContentDubber:
    """
    AI Dubbing Agent using VoxCPM (Local Neural TTS).
    """

    def __init__(self) -> None:
        self.output_dir: Path = config.PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize VoxCPM engine
        self._engine: VoxCPMEngine | None = None
        if VOXCPM_AVAILABLE:
            self._engine = VoxCPMEngine(output_dir=self.output_dir)

    def dub_content(
        self, text: str, lang: str = "English", voice: str | None = None
    ) -> tuple[str | None, str | None]:
        """
        Generates audio from text.

        Args:
            text: Text to convert to speech.
            lang: Target language (currently informational, VoxCPM handles multi-lang).
            voice: Voice name or reference audio path for voice cloning.

        Returns:
            Tuple of (text, audio_filepath)
        """
        if not VOXCPM_AVAILABLE or self._engine is None:
            logger.warning("⚠️ VoxCPM not installed. Dubbing disabled.")
            return None, None

        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        filename = f"dub_{lang}_{text_hash}.wav"
        path = self.output_dir / filename

        try:
            result = self._engine.generate(
                text=text,
                voice=voice,
                output_path=path,
            )

            if result and Path(result).exists() and Path(result).stat().st_size > 0:
                logger.info(f"🎙️ Dubbing complete: {filename}")
                return text, result
            else:
                logger.error("❌ Dubbing failed: Output file is empty.")
                return None, None

        except Exception as e:
            logger.error(f"❌ Dubbing Error: {e}")
            return None, None
