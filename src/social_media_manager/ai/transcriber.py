import logging
from pathlib import Path

import torch

from ..config import config

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Handles video transcription using OpenAI's Whisper model.
    """

    def __init__(self, model_size: str = "base") -> None:
        try:
            import whisper

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"🚀 Loading Whisper on: {self.device.upper()}")
            self.model = whisper.load_model(model_size, device=self.device)
        except ImportError:
            logger.error("❌ Whisper not installed!")
            self.model = None
        except Exception as e:
            logger.error(f"❌ Whisper Init Failed: {e}")
            self.model = None

    def generate_srt(self, video_path: str) -> str | None:
        """
        Generate an SRT subtitle file for a video.
        """
        if not self.model:
            return None

        path_obj = Path(video_path)
        if not path_obj.exists():
            logger.error(f"❌ Video not found: {video_path}")
            return None

        try:
            logger.info(f"🗣️ Transcribing {path_obj.name}...")
            # Use vocabulary from config to improve accuracy
            vocabulary = "Social Media, Viral, " + config.get("vocabulary", "")

            result = self.model.transcribe(
                str(video_path),
                fp16=(self.device == "cuda"),
                initial_prompt=f"Keywords: {vocabulary}",
            )

            srt_path = path_obj.with_suffix(".srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(result["segments"], 1):
                    start = self._fmt(segment["start"])
                    end = self._fmt(segment["end"])
                    text = segment["text"].strip()
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

            return str(srt_path)
        except Exception as e:
            logger.error(f"❌ Transcribe error: {e}")
            return None

    def _fmt(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
