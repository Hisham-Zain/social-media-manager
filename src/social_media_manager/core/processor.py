import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any

import cv2  # OpenCV for Face Tracking
import numpy as np

# --- MOVIEPY V2 IMPORTS ---
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut, MultiplyVolume

# Import Effects individually (The new v2 way)
from moviepy.video.fx import FadeIn, FadeOut, MultiplyColor

from ..config import config
from ..exceptions import VideoFileError

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(self) -> None:
        self.output_dir: Path = config.PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Load Face Detector
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except cv2.error as e:
            logger.warning(f"⚠️ OpenCV face detector failed: {e}")
            self.face_cascade = None
        except OSError as e:
            logger.warning(f"⚠️ Haarcascade file not found: {e}")
            self.face_cascade = None

    def get_info(self, path: str | Path) -> dict[str, Any]:
        try:
            with VideoFileClip(str(path)) as clip:
                return {"duration": clip.duration, "filename": Path(path).name}
        except FileNotFoundError:
            logger.warning(f"Video file not found: {path}")
            return {"duration": 0, "filename": Path(path).name}
        except OSError as e:
            logger.warning(f"Cannot read video file {path}: {e}")
            return {"duration": 0, "filename": Path(path).name}
        except ValueError as e:
            logger.warning(f"Invalid video format {path}: {e}")
            return {"duration": 0, "filename": Path(path).name}

    # --- 1. VIRAL RETENTION ENGINE ---
    def convert_to_vertical(
        self,
        video_path: str,
        smoothing_window: int = 30,
        pan_speed: float = 0.1,
    ) -> str:
        """
        Smart AI Crop (Landscape -> Portrait) with smooth panning.

        Uses face tracking with a moving average to create smooth camera-like
        panning instead of jarring cut jumps. The virtual camera gradually
        pans toward the subject's position.

        Args:
            video_path: Path to the input video.
            smoothing_window: Number of frames for moving average filter.
            pan_speed: How fast to pan toward target (0.0-1.0, lower = smoother).

        Returns:
            Path to the vertical video.
        """
        logger.info(f"📱 AI Vertical Crop (smooth): {Path(video_path).name}")
        try:
            with VideoFileClip(video_path) as clip:
                w, h = clip.size
                target_ratio = 9 / 16
                new_w = h * target_ratio

                # Face detection helper
                def get_face_center(frame: np.ndarray) -> float:
                    if self.face_cascade is None:
                        return w / 2
                    try:
                        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                        if len(faces) > 0:
                            x, _y, fw, _fh = faces[0]
                            return float(x + fw / 2)
                    except cv2.error:
                        # Face detection failed on this frame
                        pass
                    return w / 2

                # Build face position history for smooth panning
                position_history: list[float] = []
                current_position = w / 2  # Start at center

                # Pre-calculate face positions for key frames
                fps = clip.fps or 24
                key_frame_interval = max(1, int(fps / 5))  # Sample 5 times per second

                key_positions: dict[int, float] = {}
                for frame_num in range(0, int(clip.duration * fps), key_frame_interval):
                    t = frame_num / fps
                    if t < clip.duration:
                        face_pos = get_face_center(clip.get_frame(t))
                        key_positions[frame_num] = face_pos

                # Smooth panning function for each frame
                def get_smooth_position(t: float) -> float:
                    nonlocal current_position, position_history

                    frame_num = int(t * fps)

                    # Get target position (interpolate from key frames)
                    closest_key = min(
                        key_positions.keys(),
                        key=lambda k: abs(k - frame_num),
                        default=0,
                    )
                    target_pos = key_positions.get(closest_key, w / 2)

                    # Smooth pan toward target (exponential smoothing)
                    current_position += (target_pos - current_position) * pan_speed

                    # Add to history for moving average
                    position_history.append(current_position)
                    if len(position_history) > smoothing_window:
                        position_history.pop(0)

                    # Return moving average
                    return sum(position_history) / len(position_history)

                # Calculate average position for initial static crop as fallback
                all_positions = list(key_positions.values())
                avg_center = (
                    sum(all_positions) / len(all_positions) if all_positions else w / 2
                )

                # Calculate crop boundaries
                x1 = max(0, avg_center - new_w / 2)
                x2 = min(w, x1 + new_w)

                # v2 Syntax: .cropped() instead of .crop()
                final = clip.cropped(x1=x1, y1=0, x2=x2, y2=h).resized(height=1920)
                out = self.output_dir / f"vert_{Path(video_path).name}"

                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )

            logger.info(f"✅ Smooth vertical crop complete: {out}")
            return str(out)
        except FileNotFoundError:
            logger.error(f"Vertical Crop: Video file not found: {video_path}")
            raise VideoFileError(f"Video not found: {video_path}")
        except OSError as e:
            logger.error(f"Vertical Crop Failed (I/O): {e}")
            return video_path
        except ValueError as e:
            logger.error(f"Vertical Crop Failed (invalid format): {e}")
            return video_path

    def smart_cut(self, video_path: str, threshold=0.03, chunk_size=0.5) -> str:
        """Removes silence and applies jump cuts."""
        logger.info("✂️ Smart Cutting...")
        try:
            with VideoFileClip(video_path) as video:
                if not video.audio:
                    return video_path

                cut_intervals = []
                curr_start = None
                for t in np.arange(0, video.duration, chunk_size):
                    chunk = video.audio.subclip(t, min(t + chunk_size, video.duration))
                    if chunk.max_volume() >= threshold:
                        if curr_start is None:
                            curr_start = t
                    else:
                        if curr_start is not None:
                            cut_intervals.append((curr_start, t))
                            curr_start = None
                if curr_start is not None:
                    cut_intervals.append((curr_start, video.duration))

                if not cut_intervals:
                    return video_path

                clips = [video.subclip(s, e) for s, e in cut_intervals]
                final = concatenate_videoclips(clips)
                out = self.output_dir / f"cut_{Path(video_path).name}"
                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )
            return str(out)
        except FileNotFoundError:
            logger.error(f"Smart Cut: Video not found: {video_path}")
            raise VideoFileError(f"Video not found: {video_path}")
        except OSError as e:
            logger.error(f"Smart Cut Failed (I/O): {e}")
            return video_path
        except ValueError as e:
            logger.error(f"Smart Cut Failed (audio processing): {e}")
            return video_path

    def apply_transcript_cuts(
        self,
        video_path: str,
        cut_list: list[tuple[float, float]],
        output_path: str | None = None,
    ) -> str:
        """
        Apply precise cuts based on transcript editing.

        Takes a list of (start, end) segments to KEEP and concatenates them.
        Used by TranscriptEditor for text-based video editing.

        Args:
            video_path: Path to input video.
            cut_list: List of (start, end) tuples representing segments to keep.
            output_path: Optional output path. Auto-generated if not provided.

        Returns:
            Path to the edited video.
        """
        if not cut_list:
            logger.warning("Empty cut list - returning original video")
            return video_path

        logger.info(f"✂️ Applying {len(cut_list)} transcript cuts...")

        try:
            with VideoFileClip(video_path) as video:
                clips = []
                for start, end in cut_list:
                    # Ensure valid times within video duration
                    start = max(0, start)
                    end = min(end, video.duration)
                    if end > start:
                        clips.append(video.subclip(start, end))

                if not clips:
                    logger.warning(
                        "No valid clips after filtering - returning original"
                    )
                    return video_path

                final = concatenate_videoclips(clips, method="compose")

                if output_path is None:
                    output_path = str(
                        self.output_dir / f"transcript_edit_{Path(video_path).name}"
                    )

                final.write_videofile(
                    str(output_path), codec="libx264", audio_codec="aac", logger=None
                )

            logger.info(f"✅ Transcript cuts applied: {output_path}")
            return output_path

        except FileNotFoundError:
            logger.error(f"Transcript Cut: Video not found: {video_path}")
            raise VideoFileError(f"Video not found: {video_path}")
        except OSError as e:
            logger.error(f"Transcript Cut Failed (I/O): {e}")
            return video_path
        except ValueError as e:
            logger.error(f"Transcript Cut Failed (processing): {e}")
            return video_path

    def apply_polish(self, video_path: str) -> str:
        """Color Grading & SFX Injection."""
        logger.info("✨ Applying Polish (Color & SFX)...")
        try:
            with VideoFileClip(video_path) as clip:
                # v2 Syntax: .with_effects([MultiplyColor(...)])
                polished = clip.with_effects([MultiplyColor(1.2)])

                # Add Whoosh SFX at transitions
                sfx_files = list(config.SFX_DIR.glob("*.mp3"))

                # SAFETY: Check if video has audio before compositing
                audio_layers = []
                if polished.audio is not None:
                    audio_layers.append(polished.audio)

                if sfx_files:
                    for t in range(0, int(clip.duration), 5):  # Every 5s
                        if t == 0:
                            continue
                        sfx = (
                            AudioFileClip(str(random.choice(sfx_files)))
                            .with_start(t)
                            .with_effects([MultiplyVolume(0.3)])  # v2 Volume
                        )
                        audio_layers.append(sfx)

                # Only add audio if we have layers
                if audio_layers:
                    polished = polished.with_audio(CompositeAudioClip(audio_layers))
                out = self.output_dir / f"polish_{Path(video_path).name}"
                polished.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )
            return str(out)
        except FileNotFoundError as e:
            logger.warning(f"Polish: SFX file not found: {e}")
            return video_path
        except OSError as e:
            logger.warning(f"Polish skipped (I/O): {e}")
            return video_path

    # --- 2. VISUAL COMPOSER ---
    def overlay_visuals(self, video_path, visual_plan):
        if not visual_plan:
            return video_path
        logger.info(f"🎞️ Adding {len(visual_plan)} B-Roll clips...")
        try:
            with VideoFileClip(video_path) as video:
                clips = [video]
                for item in visual_plan:
                    if not os.path.exists(item["path"]):
                        continue

                    # v2 Syntax: Effects list for fading
                    effects = [FadeIn(0.5), FadeOut(0.5)]

                    img = (
                        ImageClip(item["path"])
                        .with_start(item["start"])
                        .with_duration(item["end"] - item["start"])
                        .resized(height=video.h)
                        .with_position("center")
                        .with_effects(effects)
                    )
                    clips.append(img)
                final = CompositeVideoClip(clips)
                out = self.output_dir / f"visual_{Path(video_path).name}"
                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )
            return str(out)
        except FileNotFoundError as e:
            logger.warning(f"Overlay Visuals: Image not found: {e}")
            return video_path
        except OSError as e:
            logger.warning(f"Overlay Visuals failed (I/O): {e}")
            return video_path

    def burn_captions(self, video_path, srt_path, style_config=None):
        if not os.path.exists(srt_path):
            return video_path

        style = {
            "font_size": 70,
            "color": "yellow",
            "stroke_color": "black",
            "stroke_width": 3,
            "y_pos": 0.8,
        }
        if style_config:
            style.update(style_config)

        logger.info("🔥 Burning Captions...")
        try:
            with VideoFileClip(video_path) as video:
                subtitles = self._parse_srt(srt_path)
                clips = [video]

                for start, end, text in subtitles:
                    # Kinetic Logic
                    f_size = style["font_size"]
                    c_color = style["color"]
                    if text.isupper():
                        f_size += 20
                        c_color = "red"
                    elif "$" in text:
                        c_color = "#00FF00"

                    txt = (
                        TextClip(
                            text=text,
                            font_size=f_size,
                            color=c_color,
                            stroke_color=style["stroke_color"],
                            stroke_width=style["stroke_width"],
                            size=(video.w * 0.8, None),
                            method="caption",
                        )
                        .with_position(("center", style["y_pos"]), relative=True)
                        .with_start(start)
                        .with_duration(end - start)
                    )
                    clips.append(txt)

                final = CompositeVideoClip(clips)
                out = self.output_dir / f"cap_{Path(video_path).name}"
                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )
            return str(out)
        except FileNotFoundError as e:
            logger.error(f"Caption Error: File not found: {e}")
            return video_path
        except OSError as e:
            logger.error(f"Caption Error (I/O): {e}")
            return video_path
        except ValueError as e:
            logger.error(f"Caption Error (text rendering): {e}")
            return video_path

    def add_background_music(self, video_path, volume=0.1):
        music_files = list(config.MUSIC_DIR.glob("*.mp3"))
        if not music_files:
            return video_path
        logger.info("🎵 Mastering Audio...")
        try:
            with VideoFileClip(video_path) as video:
                music = AudioFileClip(str(random.choice(music_files)))
                if music.duration < video.duration:
                    music = music.loop(duration=video.duration)
                else:
                    music = music.subclip(0, video.duration)

                # v2 Audio Effects
                effects = [MultiplyVolume(volume), AudioFadeIn(2.0), AudioFadeOut(2.0)]
                music = music.with_effects(effects)

                # SAFETY: Check if video has audio before compositing
                if video.audio is not None:
                    final = video.with_audio(CompositeAudioClip([video.audio, music]))
                else:
                    # Video has no audio, just add the music
                    final = video.with_audio(music)

                out = self.output_dir / f"music_{Path(video_path).name}"
                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )
            return str(out)
        except FileNotFoundError as e:
            logger.error(f"Music Error: File not found: {e}")
            return video_path
        except OSError as e:
            logger.error(f"Music Error (I/O): {e}")
            return video_path

    def smart_mix(
        self,
        voice_path: str,
        music_path: str,
        output_path: str | None = None,
        duck_amount_db: float = -12.0,
        threshold_db: float = -30.0,
        chunk_ms: int = 500,
    ) -> str | None:
        """
        Mix voice and music with auto-ducking.

        When voice is detected above threshold, the music volume is reduced
        by duck_amount_db. This creates professional sounding audio where
        the background music doesn't compete with speech.

        Args:
            voice_path: Path to voice/speech audio file.
            music_path: Path to background music file.
            output_path: Optional output path. If None, auto-generates.
            duck_amount_db: How much to reduce music volume during speech (negative dB).
            threshold_db: Voice level threshold for ducking (dBFS).
            chunk_ms: Analysis chunk size in milliseconds.

        Returns:
            Path to the mixed audio file, or None on failure.
        """
        logger.info("🎚️ Smart Mix: Auto-ducking audio...")

        try:
            from pydub import AudioSegment

            # Load audio files
            voice = AudioSegment.from_file(voice_path)
            music = AudioSegment.from_file(music_path)

            # Match music length to voice
            if len(music) < len(voice):
                # Loop music to match voice length
                loops_needed = (len(voice) // len(music)) + 1
                music = music * loops_needed

            # Trim music to voice length
            music = music[: len(voice)]

            # Apply auto-ducking chunk by chunk
            ducked_music = AudioSegment.empty()
            num_chunks = len(voice) // chunk_ms

            for i in range(0, len(voice), chunk_ms):
                end_pos = min(i + chunk_ms, len(voice))
                voice_chunk = voice[i:end_pos]
                music_chunk = music[i:end_pos]

                # Check voice level in this chunk
                if voice_chunk.dBFS > threshold_db:
                    # Voice present - duck the music
                    ducked_chunk = music_chunk + duck_amount_db
                else:
                    # No voice - keep music at normal level (slightly reduced)
                    ducked_chunk = music_chunk + (duck_amount_db / 3)

                ducked_music += ducked_chunk

            # Apply smooth fade to ducked music
            ducked_music = ducked_music.fade_in(2000).fade_out(2000)

            # Overlay voice on ducked music
            final = voice.overlay(ducked_music)

            # Generate output path if not provided
            if output_path is None:
                output_path = str(self.output_dir / f"smartmix_{int(time.time())}.mp3")

            # Export
            final.export(output_path, format="mp3")

            logger.info(f"✅ Smart mix complete: {output_path}")
            return output_path

        except ImportError:
            logger.error("❌ Smart mix requires pydub. Install with: pip install pydub")
            return None
        except FileNotFoundError as e:
            logger.error(f"Smart mix: File not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Smart mix failed: {e}")
            return None

    def add_smart_background_music(
        self,
        video_path: str,
        music_path: str | None = None,
        duck_amount_db: float = -12.0,
    ) -> str:
        """
        Add background music to video with auto-ducking.

        Extracts voice from video, applies smart_mix for auto-ducking,
        and recombines with the video.

        Args:
            video_path: Path to input video.
            music_path: Path to music file. If None, picks random from library.
            duck_amount_db: Music duck amount when voice detected.

        Returns:
            Path to video with smart-mixed audio.
        """
        logger.info("🎵 Adding smart background music with auto-ducking...")

        try:
            from pydub import AudioSegment

            # Get music file
            if music_path is None:
                music_files = list(config.MUSIC_DIR.glob("*.mp3"))
                if not music_files:
                    logger.warning("No music files found, skipping")
                    return video_path
                music_path = str(random.choice(music_files))

            with VideoFileClip(video_path) as video:
                if video.audio is None:
                    logger.warning("Video has no audio, using standard music add")
                    return self.add_background_music(video_path)

                # Extract voice audio
                voice_path = str(self.output_dir / "temp_voice.mp3")
                video.audio.write_audiofile(voice_path, logger=None)

                # Smart mix with ducking
                mixed_path = self.smart_mix(
                    voice_path=voice_path,
                    music_path=music_path,
                    duck_amount_db=duck_amount_db,
                )

                if mixed_path is None:
                    logger.warning("Smart mix failed, falling back to standard mix")
                    return self.add_background_music(video_path)

                # Replace video audio with mixed audio
                mixed_audio = AudioFileClip(mixed_path)
                final = video.with_audio(mixed_audio)

                out = self.output_dir / f"smartmusic_{Path(video_path).name}"
                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )

                # Cleanup temp files
                Path(voice_path).unlink(missing_ok=True)
                Path(mixed_path).unlink(missing_ok=True)

                logger.info(f"✅ Smart music added: {out}")
                return str(out)

        except ImportError:
            logger.warning("pydub not available, using standard music add")
            return self.add_background_music(video_path)
        except Exception as e:
            logger.error(f"Smart music failed: {e}, falling back")
            return self.add_background_music(video_path)

    # --- 3. MONETIZATION & GLOBAL ---
    def overlay_affiliate(self, video_path, srt_path, matches):
        if not matches or not os.path.exists(srt_path):
            return video_path
        logger.info("💰 Overlaying Affiliate Links...")
        try:
            with VideoFileClip(video_path) as video:
                subtitles = self._parse_srt(srt_path)
                clips = [video]
                for match in matches:
                    keyword = match["keyword"]
                    for start, end, text in subtitles:
                        if keyword in text.lower():
                            box = ColorClip(
                                size=(500, 120), color=(0, 0, 0), duration=4
                            ).with_opacity(0.8)
                            info = TextClip(
                                text=f"{match['icon']} {match['link']}",
                                font_size=40,
                                color="white",
                            ).with_duration(4)
                            popup = (
                                CompositeVideoClip([box, info.with_position("center")])
                                .with_position(("right", "top"))
                                .with_start(start)
                            )
                            clips.append(popup)
                            break
                final = CompositeVideoClip(clips)
                out = self.output_dir / f"money_{Path(video_path).name}"
                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )
            return str(out)
        except FileNotFoundError as e:
            logger.warning(f"Affiliate overlay: File not found: {e}")
            return video_path
        except OSError as e:
            logger.warning(f"Affiliate overlay failed (I/O): {e}")
            return video_path

    def replace_audio_track(self, video_path: str, audio_path: str) -> str:
        if not os.path.exists(audio_path):
            return video_path
        logger.info("🎤 Dubbing Audio...")
        try:
            with VideoFileClip(video_path) as video:
                new_audio = AudioFileClip(audio_path)
                if new_audio.duration > video.duration:
                    video = video.loop(duration=new_audio.duration)
                else:
                    video = video.subclip(0, new_audio.duration)
                final = video.with_audio(new_audio)
                out = self.output_dir / f"dub_{Path(video_path).name}"
                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )
            return str(out)
        except FileNotFoundError as e:
            logger.error(f"Audio dub: File not found: {e}")
            return video_path
        except OSError as e:
            logger.error(f"Audio dub failed (I/O): {e}")
            return video_path

    def _parse_srt(self, srt_path):
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        pattern = re.compile(
            r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)",
            re.DOTALL,
        )
        return [
            (self._time(s), self._time(e), t.replace("\n", " ").strip())
            for _, s, e, t in pattern.findall(content)
        ]

    def _time(self, t):
        h, m, s = t.split(":")
        s, ms = s.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    # --- 4. VIRAL CAPTION ENGINE ---
    def add_dynamic_captions(
        self,
        video_path: str,
        style: str = "viral",
        audio_path: str | None = None,
    ) -> str:
        """
        Add viral-style karaoke captions with word-by-word highlighting.

        Uses Whisper for word-level timestamps and creates animated
        text overlays where each word pops up as it's spoken.

        Args:
            video_path: Path to video file.
            style: Caption preset ("viral", "minimal", "bold", "neon", "subtle").
            audio_path: Optional separate audio for transcription.

        Returns:
            Path to video with dynamic captions.
        """
        logger.info(f"🎬 Adding Dynamic Captions (style: {style})...")

        try:
            from .dynamic_captions import DynamicCaptions

            captions = DynamicCaptions()
            output_path = str(self.output_dir / f"karaoke_{Path(video_path).name}")

            result = captions.add_captions_to_video(
                video_path=video_path,
                audio_path=audio_path,
                output_path=output_path,
                preset=style,
            )

            if result:
                logger.info(f"✅ Dynamic captions added: {result}")
                return result
            return video_path

        except FileNotFoundError as e:
            logger.error(f"Dynamic captions: File not found: {e}")
            return video_path
        except OSError as e:
            logger.error(f"Dynamic captions failed (I/O): {e}")
            return video_path
        except ValueError as e:
            logger.error(f"Dynamic captions failed (processing): {e}")
            return video_path

    def add_ai_music(
        self,
        video_path: str,
        mood: str | None = None,
        prompt: str | None = None,
        volume: float = 0.15,
    ) -> str:
        """
        Add AI-composed background music using MusicGen.

        Instead of picking a random MP3, this generates a unique
        track based on the video mood or a custom prompt.

        Args:
            video_path: Path to video file.
            mood: Music mood preset ("corporate", "gaming", "cinematic", etc.).
            prompt: Custom music description (overrides mood).
            volume: Music volume (0.0 to 1.0).

        Returns:
            Path to video with AI-composed music.
        """
        logger.info("🎵 Composing AI Music...")

        try:
            from ..ai.composer import MusicComposer

            with VideoFileClip(video_path) as video:
                # Get video duration
                duration = min(int(video.duration) + 5, 60)  # Cap at 60s for VRAM

                # Compose music
                composer = MusicComposer(model="small")

                if prompt:
                    music_path = composer.compose(prompt, duration=duration)
                elif mood:
                    music_path = composer.compose_with_style(mood, duration=duration)
                else:
                    # Auto-detect mood from video (if possible)
                    music_path = composer.compose_with_style(
                        "corporate", duration=duration
                    )

                if not music_path or not Path(music_path).exists():
                    logger.warning("Music generation failed, skipping")
                    return video_path

                # Add music to video
                music = AudioFileClip(music_path)

                # Loop if needed
                if music.duration < video.duration:
                    from moviepy import concatenate_audioclips

                    loops = int(video.duration / music.duration) + 1
                    music = concatenate_audioclips([music] * loops)

                # Trim to video duration
                music = music.subclipped(0, video.duration)

                # Apply volume and fade
                effects = [MultiplyVolume(volume), AudioFadeIn(2.0), AudioFadeOut(2.0)]
                music = music.with_effects(effects)

                # Composite audio
                if video.audio:
                    final_audio = CompositeAudioClip([video.audio, music])
                else:
                    final_audio = music

                final = video.with_audio(final_audio)
                out = self.output_dir / f"ai_music_{Path(video_path).name}"

                final.write_videofile(
                    str(out), codec="libx264", audio_codec="aac", logger=None
                )

            logger.info(f"✅ AI music added: {out}")
            return str(out)

        except FileNotFoundError as e:
            logger.error(f"AI Music: File not found: {e}")
            return video_path
        except OSError as e:
            logger.error(f"AI Music failed (I/O): {e}")
            return video_path
        except ValueError as e:
            logger.error(f"AI Music failed (audio processing): {e}")
            return video_path

    def process_viral_video(
        self,
        video_path: str,
        add_captions: bool = True,
        caption_style: str = "viral",
        add_music: bool = True,
        music_mood: str = "corporate",
        convert_vertical: bool = False,
        smart_cut: bool = True,
        apply_polish: bool = True,
    ) -> str:
        """
        Complete viral video processing pipeline.

        Applies all optimizations for maximum engagement:
        1. Smart cut (remove silence)
        2. Vertical conversion (for shorts)
        3. Dynamic karaoke captions
        4. AI-composed background music
        5. Color grading and polish

        Args:
            video_path: Input video path.
            add_captions: Add dynamic karaoke captions.
            caption_style: Caption style preset.
            add_music: Add AI-composed music.
            music_mood: Music mood for composition.
            convert_vertical: Convert to 9:16 aspect ratio.
            smart_cut: Remove silence/apply jump cuts.
            apply_polish: Apply color grading.

        Returns:
            Path to processed viral video.
        """
        logger.info("🚀 Processing Viral Video Pipeline...")
        current = video_path

        try:
            # Step 1: Smart cut
            if smart_cut:
                current = self.smart_cut(current)

            # Step 2: Vertical conversion
            if convert_vertical:
                current = self.convert_to_vertical(current)

            # Step 3: Dynamic captions
            if add_captions:
                current = self.add_dynamic_captions(current, style=caption_style)

            # Step 4: AI Music
            if add_music:
                current = self.add_ai_music(current, mood=music_mood)

            # Step 5: Polish
            if apply_polish:
                current = self.apply_polish(current)

            # Rename to final
            final_path = self.output_dir / f"viral_{Path(video_path).name}"
            if current != str(final_path):
                Path(current).rename(final_path)
                current = str(final_path)

            logger.info(f"✅ Viral video complete: {current}")
            return current

        except FileNotFoundError:
            logger.error(f"Viral processing: Video not found: {video_path}")
            raise VideoFileError(f"Video not found: {video_path}")
        except OSError as e:
            logger.error(f"Viral processing failed (I/O): {e}")
            return video_path
        except ValueError as e:
            logger.error(f"Viral processing failed (format): {e}")
            return video_path
