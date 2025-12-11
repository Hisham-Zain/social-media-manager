import logging
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

from ..config import config

logger = logging.getLogger(__name__)


class AvatarEngine:
    """Generates talking head videos from audio using avatar images."""

    def __init__(self) -> None:
        self.closed_path: Path = config.AVATAR_DIR / "closed.png"
        self.open_path: Path = config.AVATAR_DIR / "open.png"

    def generate_talking_head(self, audio_path: str | Path) -> str | None:
        """
        Generate a talking head video from audio.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Path to the generated video, or None if generation failed.
        """
        if not self.closed_path.exists():
            logger.warning(f"⚠️ Avatar missing: {self.closed_path}")
            return None

        logger.info("🤖 Animating Avatar...")
        try:
            with AudioFileClip(str(audio_path)) as audio:
                clips = []
                chunk_size = 0.1

                for t in np.arange(0, audio.duration, chunk_size):
                    end_t = min(t + chunk_size, audio.duration)
                    chunk = audio.subclip(t, end_t)

                    # Volume threshold
                    img = (
                        self.open_path
                        if chunk.max_volume() > 0.01
                        else self.closed_path
                    )
                    clips.append(ImageClip(str(img)).with_duration(end_t - t))

                video = concatenate_videoclips(clips, method="compose").with_audio(
                    audio
                )
                out = config.PROCESSED_DIR / f"avatar_{Path(audio_path).stem}.mp4"
                video.write_videofile(
                    str(out), fps=24, codec="libx264", audio_codec="aac", logger=None
                )

            return str(out)
        except Exception as e:
            logger.error(f"Avatar Gen Failed: {e}")
            return None
