"""
Dynamic Captions Generator for AgencyOS.

Creates viral-style animated captions with:
- Word-by-word karaoke highlighting
- Pop-up animations
- Custom styling per word
- Whisper word-level timestamp support

Inspired by popular short-form video captions.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger


@dataclass
class WordTiming:
    """Single word with timing information."""

    word: str
    start: float  # Start time in seconds
    end: float  # End time in seconds
    confidence: float = 1.0


@dataclass
class CaptionSegment:
    """A segment of caption (usually a sentence or phrase)."""

    text: str
    start: float
    end: float
    words: list[WordTiming] = field(default_factory=list)


@dataclass
class CaptionStyle:
    """Styling options for captions."""

    # Font settings
    font: str = "Arial-Bold"
    font_size: int = 60

    # Colors (can be hex or color name)
    text_color: str = "white"
    highlight_color: str = "#00FF00"  # Green for active word
    shadow_color: str = "black"
    outline_color: str = "black"

    # Effects
    outline_width: int = 3
    shadow_offset: tuple[int, int] = (3, 3)

    # Animation
    animation: Literal["none", "pop", "bounce", "fade", "slide"] = "pop"
    animation_duration: float = 0.15  # Duration of pop/bounce effect

    # Layout
    position: Literal["bottom", "center", "top"] = "bottom"
    max_words_per_line: int = 4
    margin_bottom: int = 100
    margin_side: int = 50


class DynamicCaptions:
    """
    Generate viral-style dynamic captions.

    Features:
    - Word-by-word karaoke highlighting
    - Pop-up animations for each word
    - Custom styling (colors, fonts, effects)
    - Whisper integration for accurate timing

    Example:
        captions = DynamicCaptions()

        # Get word timings from Whisper
        segments = captions.transcribe_with_words("audio.mp3")

        # Generate caption clips
        clips = captions.generate_clips(
            segments,
            video_size=(1080, 1920),
            style=CaptionStyle(highlight_color="#FF0000")
        )

        # Add to video
        final = CompositeVideoClip([video] + clips)
    """

    # Preset styles for different vibes
    PRESETS = {
        "viral": CaptionStyle(
            font="Arial-Bold",
            font_size=70,
            text_color="white",
            highlight_color="#00FF00",
            animation="pop",
            outline_width=4,
        ),
        "minimal": CaptionStyle(
            font="Helvetica",
            font_size=50,
            text_color="white",
            highlight_color="yellow",
            animation="fade",
            outline_width=2,
        ),
        "bold": CaptionStyle(
            font="Impact",
            font_size=80,
            text_color="yellow",
            highlight_color="#FF0000",
            animation="bounce",
            outline_width=5,
        ),
        "subtle": CaptionStyle(
            font="Arial",
            font_size=45,
            text_color="#CCCCCC",
            highlight_color="white",
            animation="none",
            outline_width=1,
        ),
        "neon": CaptionStyle(
            font="Arial-Bold",
            font_size=65,
            text_color="#00FFFF",
            highlight_color="#FF00FF",
            animation="pop",
            outline_width=3,
        ),
    }

    def __init__(self):
        """Initialize DynamicCaptions."""
        self._transcriber = None
        logger.info("🎬 DynamicCaptions initialized")

    @property
    def transcriber(self):
        """Lazy load Whisper transcriber."""
        if self._transcriber is None:
            from ..ai.transcriber import WhisperTranscriber

            self._transcriber = WhisperTranscriber(model="base")
        return self._transcriber

    def transcribe_with_words(self, audio_path: str) -> list[CaptionSegment]:
        """
        Transcribe audio and get word-level timestamps using Whisper.

        Args:
            audio_path: Path to audio file.

        Returns:
            List of caption segments with word timings.
        """
        logger.info(f"📝 Transcribing with word timestamps: {audio_path}")

        try:
            # Use Whisper with word timestamps
            result = self.transcriber.transcribe(audio_path, word_timestamps=True)

            segments = []

            for segment in result.get("segments", []):
                words = []

                for word_info in segment.get("words", []):
                    words.append(
                        WordTiming(
                            word=word_info["word"].strip(),
                            start=word_info["start"],
                            end=word_info["end"],
                            confidence=word_info.get("probability", 1.0),
                        )
                    )

                if words:
                    segments.append(
                        CaptionSegment(
                            text=segment["text"].strip(),
                            start=segment["start"],
                            end=segment["end"],
                            words=words,
                        )
                    )

            logger.info(
                f"✅ Transcribed {len(segments)} segments with {sum(len(s.words) for s in segments)} words"
            )
            return segments

        except FileNotFoundError as e:
            logger.error(f"Transcription failed: Audio file not found: {e}")
            return []
        except ImportError as e:
            logger.error(f"Transcription failed: Whisper not available: {e}")
            return []
        except RuntimeError as e:
            logger.error(f"Transcription failed (Whisper runtime): {e}")
            return []
        except Exception as e:
            logger.error(f"Transcription failed ({type(e).__name__}): {e}")
            return []

    def generate_clips(
        self,
        segments: list[CaptionSegment],
        video_size: tuple[int, int],
        style: CaptionStyle | None = None,
        preset: str | None = None,
    ) -> list:
        """
        Generate TextClip objects for each word with karaoke highlighting.

        Args:
            segments: Caption segments with word timings.
            video_size: (width, height) of video.
            style: Custom caption style.
            preset: Use preset style by name.

        Returns:
            List of MoviePy TextClip objects.
        """

        # Get style
        if preset and preset in self.PRESETS:
            style = self.PRESETS[preset]
        elif style is None:
            style = self.PRESETS["viral"]

        clips = []
        video_width, video_height = video_size

        # Calculate position based on style
        if style.position == "bottom":
            y_pos = video_height - style.margin_bottom - style.font_size
        elif style.position == "top":
            y_pos = style.margin_bottom
        else:  # center
            y_pos = video_height // 2

        for segment in segments:
            # Group words into lines
            lines = self._split_into_lines(segment.words, style.max_words_per_line)

            for line_idx, line_words in enumerate(lines):
                # Calculate line timing
                line_start = line_words[0].start
                line_end = line_words[-1].end

                # Adjust y position for multiple lines
                line_y = y_pos - (len(lines) - line_idx - 1) * (style.font_size + 10)

                # Generate clips for this line
                line_clips = self._generate_line_clips(
                    line_words,
                    video_width,
                    line_y,
                    style,
                    line_start,
                    line_end,
                )
                clips.extend(line_clips)

        logger.info(f"✅ Generated {len(clips)} caption clips")
        return clips

    def _split_into_lines(
        self, words: list[WordTiming], max_words: int
    ) -> list[list[WordTiming]]:
        """Split words into lines based on max words per line."""
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            if len(current_line) >= max_words:
                lines.append(current_line)
                current_line = []

        if current_line:
            lines.append(current_line)

        return lines

    def _generate_line_clips(
        self,
        words: list[WordTiming],
        video_width: int,
        y_pos: int,
        style: CaptionStyle,
        line_start: float,
        line_end: float,
    ) -> list:
        """Generate clips for a single line of words."""
        from moviepy import TextClip

        clips = []

        # Calculate total line width for centering
        line_text = " ".join(w.word for w in words)

        # Create a reference clip to measure width
        try:
            ref_clip = TextClip(
                text=line_text,
                font=style.font,
                font_size=style.font_size,
            )
            total_width = ref_clip.w
            ref_clip.close()
        except OSError:
            # Font not found or moviepy issue - fallback
            total_width = int(len(line_text) * style.font_size * 0.5)

        # Starting x position (centered)
        x_offset = (video_width - total_width) // 2

        for word_idx, word in enumerate(words):
            # Calculate word position
            preceding_text = " ".join(w.word for w in words[:word_idx])
            if preceding_text:
                preceding_text += " "

            try:
                if preceding_text:
                    preceding_clip = TextClip(
                        text=preceding_text,
                        font=style.font,
                        font_size=style.font_size,
                    )
                    word_x = x_offset + preceding_clip.w
                    preceding_clip.close()
                else:
                    word_x = x_offset
            except OSError:
                word_x = int(x_offset + len(preceding_text) * style.font_size * 0.5)

            # Generate clips for this word
            word_clips = self._generate_word_clips(
                word,
                word_x,
                y_pos,
                style,
                line_start,
                line_end,
            )
            clips.extend(word_clips)

        return clips

    def _generate_word_clips(
        self,
        word: WordTiming,
        x_pos: int,
        y_pos: int,
        style: CaptionStyle,
        line_start: float,
        line_end: float,
    ) -> list:
        """Generate animated clips for a single word."""
        from moviepy import TextClip

        clips = []

        # Base text style
        base_kwargs = {
            "font": style.font,
            "font_size": style.font_size,
            "stroke_color": style.outline_color,
            "stroke_width": style.outline_width,
        }

        # 1. Before highlight (normal color)
        if word.start > line_start:
            before_clip = TextClip(
                text=word.word, color=style.text_color, **base_kwargs
            )
            before_clip = before_clip.with_position((x_pos, y_pos))
            before_clip = before_clip.with_start(line_start)
            before_clip = before_clip.with_end(word.start)
            clips.append(before_clip)

        # 2. During highlight (highlighted color with animation)
        highlight_duration = word.end - word.start

        if style.animation == "pop":
            # Pop animation: scale up then down
            clips.extend(
                self._create_pop_animation(word, x_pos, y_pos, style, base_kwargs)
            )
        elif style.animation == "bounce":
            clips.extend(
                self._create_bounce_animation(word, x_pos, y_pos, style, base_kwargs)
            )
        else:
            # No animation, just color change
            highlight_clip = TextClip(
                text=word.word, color=style.highlight_color, **base_kwargs
            )
            highlight_clip = highlight_clip.with_position((x_pos, y_pos))
            highlight_clip = highlight_clip.with_start(word.start)
            highlight_clip = highlight_clip.with_end(word.end)
            clips.append(highlight_clip)

        # 3. After highlight (back to normal)
        if word.end < line_end:
            after_clip = TextClip(text=word.word, color=style.text_color, **base_kwargs)
            after_clip = after_clip.with_position((x_pos, y_pos))
            after_clip = after_clip.with_start(word.end)
            after_clip = after_clip.with_end(line_end)
            clips.append(after_clip)

        return clips

    def _create_pop_animation(
        self,
        word: WordTiming,
        x_pos: int,
        y_pos: int,
        style: CaptionStyle,
        base_kwargs: dict,
    ) -> list:
        """Create pop-up animation effect."""
        from moviepy import TextClip

        clips = []
        duration = word.end - word.start
        anim_duration = min(style.animation_duration, duration / 3)

        # Pop up phase (larger size)
        pop_clip = TextClip(
            text=word.word,
            color=style.highlight_color,
            font=style.font,
            font_size=int(style.font_size * 1.2),  # 20% larger
            stroke_color=style.outline_color,
            stroke_width=style.outline_width + 1,
        )
        # Adjust position for larger size
        pop_x = x_pos - int(style.font_size * 0.1)
        pop_y = y_pos - int(style.font_size * 0.1)
        pop_clip = pop_clip.with_position((pop_x, pop_y))
        pop_clip = pop_clip.with_start(word.start)
        pop_clip = pop_clip.with_end(word.start + anim_duration)
        clips.append(pop_clip)

        # Normal size highlight phase
        highlight_clip = TextClip(
            text=word.word, color=style.highlight_color, **base_kwargs
        )
        highlight_clip = highlight_clip.with_position((x_pos, y_pos))
        highlight_clip = highlight_clip.with_start(word.start + anim_duration)
        highlight_clip = highlight_clip.with_end(word.end)
        clips.append(highlight_clip)

        return clips

    def _create_bounce_animation(
        self,
        word: WordTiming,
        x_pos: int,
        y_pos: int,
        style: CaptionStyle,
        base_kwargs: dict,
    ) -> list:
        """Create bounce animation effect."""
        from moviepy import TextClip

        clips = []
        duration = word.end - word.start
        anim_duration = min(style.animation_duration, duration / 4)

        # Bounce up
        bounce_offset = int(style.font_size * 0.15)

        bounce_clip = TextClip(
            text=word.word, color=style.highlight_color, **base_kwargs
        )
        bounce_clip = bounce_clip.with_position((x_pos, y_pos - bounce_offset))
        bounce_clip = bounce_clip.with_start(word.start)
        bounce_clip = bounce_clip.with_end(word.start + anim_duration)
        clips.append(bounce_clip)

        # Settle down
        settle_clip = TextClip(
            text=word.word, color=style.highlight_color, **base_kwargs
        )
        settle_clip = settle_clip.with_position((x_pos, y_pos))
        settle_clip = settle_clip.with_start(word.start + anim_duration)
        settle_clip = settle_clip.with_end(word.end)
        clips.append(settle_clip)

        return clips

    def add_captions_to_video(
        self,
        video_path: str,
        audio_path: str | None = None,
        output_path: str | None = None,
        style: CaptionStyle | None = None,
        preset: str = "viral",
    ) -> str | None:
        """
        Add dynamic captions to a video file.

        Args:
            video_path: Path to input video.
            audio_path: Optional separate audio file (uses video audio if None).
            output_path: Output path (auto-generated if None).
            style: Custom caption style.
            preset: Preset style name.

        Returns:
            Path to output video with captions.
        """
        from moviepy import CompositeVideoClip, VideoFileClip

        logger.info(f"🎬 Adding dynamic captions to: {video_path}")

        try:
            # Load video
            video = VideoFileClip(video_path)
            video_size = (video.w, video.h)

            # Transcribe audio
            audio_source = audio_path or video_path
            segments = self.transcribe_with_words(audio_source)

            if not segments:
                logger.warning("No segments transcribed, returning original video")
                return video_path

            # Generate caption clips
            caption_clips = self.generate_clips(
                segments,
                video_size,
                style=style,
                preset=preset,
            )

            # Composite video with captions
            final = CompositeVideoClip([video] + caption_clips)

            # Output path
            if output_path is None:
                input_path = Path(video_path)
                output_path = str(
                    input_path.parent
                    / f"{input_path.stem}_captioned{input_path.suffix}"
                )

            # Write output
            final.write_videofile(
                output_path,
                fps=video.fps or 30,
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )

            # Cleanup
            video.close()
            final.close()

            logger.info(f"✅ Captioned video saved: {output_path}")
            return output_path

        except FileNotFoundError as e:
            logger.error(f"Failed to add captions: Video file not found: {e}")
            return None
        except OSError as e:
            logger.error(f"Failed to add captions (I/O error): {e}")
            return None
        except ValueError as e:
            logger.error(f"Failed to add captions (bad value): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to add captions ({type(e).__name__}): {e}")
            return None

    def generate_srt(
        self,
        segments: list[CaptionSegment],
        output_path: str,
    ) -> str:
        """Generate SRT subtitle file from segments."""
        lines = []

        for i, segment in enumerate(segments):
            start_time = self._format_srt_time(segment.start)
            end_time = self._format_srt_time(segment.end)

            lines.append(str(i + 1))
            lines.append(f"{start_time} --> {end_time}")
            lines.append(segment.text)
            lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"📄 SRT saved: {output_path}")
        return output_path

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# Convenience functions
def add_dynamic_captions(
    video_path: str,
    preset: str = "viral",
    output_path: str | None = None,
) -> str | None:
    """Quick function to add viral-style captions to a video."""
    captions = DynamicCaptions()
    return captions.add_captions_to_video(
        video_path, preset=preset, output_path=output_path
    )


def transcribe_with_words(audio_path: str) -> list[CaptionSegment]:
    """Quick function to get word-level transcription."""
    captions = DynamicCaptions()
    return captions.transcribe_with_words(audio_path)
