import logging
from pathlib import Path

try:
    from clipsai import ClipFinder, Transcriber, resize
except ImportError:
    ClipFinder = None
    Transcriber = None
    resize = None

from ..config import config

logger = logging.getLogger(__name__)


class SmartClipper:
    """
    Handles intelligent video clipping using AI.

    Attributes:
        hf_token (str): Hugging Face token for authentication.
        transcriber (Transcriber): The transcriber instance.
        finder (ClipFinder): The clip finder instance.
    """

    def __init__(self) -> None:
        """
        Initialize the SmartClipper.
        """
        self.hf_token: str | None = config.HF_TOKEN
        self.transcriber: Any | None = None
        self.finder: Any | None = None

    def _load(self) -> None:
        """
        Lazy load the heavy AI models (Transcriber and ClipFinder).
        """
        if not self.transcriber and ClipFinder:
            logger.info("⏳ Loading ClipsAI (Medium)...")
            self.transcriber = Transcriber(model_size="medium")
            self.finder = ClipFinder()

    def create_viral_shorts(self, video_path: str | Path) -> str | None:
        """
        Create viral shorts from a long-form video.

        Args:
            video_path (str | Path): Path to the source video file.

        Returns:
            str or None: Path to the generated short video, or None if failed.
        """
        if not self.hf_token:
            return None
        self._load()
        if not self.transcriber or not self.finder:
            return None

        try:
            transcription = self.transcriber.transcribe(audio_file_path=str(video_path))
            clips = self.finder.find_clips(transcription=transcription)
            if not clips:
                return None

            best = clips[0]
            # resize is imported from clipsai, assuming it's available if ClipFinder is
            if resize:
                resize(
                    video_file_path=str(video_path),
                    pyannote_auth_token=self.hf_token,
                    aspect_ratio=(9, 16),
                    start_time=best.start_time,
                    end_time=best.end_time,
                )
                return str(
                    Path(video_path).parent / f"{Path(video_path).stem}_9_16.mp4"
                )
            return None
        except Exception as e:
            logger.error(f"Clipper Error: {e}")
            return None
