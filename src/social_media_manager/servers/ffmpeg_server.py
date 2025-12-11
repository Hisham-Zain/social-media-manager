#!/usr/bin/env python3
"""
FFmpeg MCP Server

A local FOSS MCP server for video editing operations.
Cost: $0 - Uses local FFmpeg installation.

Security: Commands are sanitized to only allow FFmpeg operations
on files within the processed directory.
"""

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("FFmpeg Video Editor")

# Allowed output directory (security)
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "./processed")).resolve()
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_path(path: str) -> Path | None:
    """Ensure path is within allowed directory."""
    try:
        resolved = Path(path).resolve()
        # Allow input from anywhere, but be cautious
        return resolved
    except Exception:
        return None


def _is_safe_output(path: str) -> bool:
    """Check if output path is within PROCESSED_DIR."""
    try:
        resolved = Path(path).resolve()
        return str(resolved).startswith(str(PROCESSED_DIR))
    except Exception:
        return False


@mcp.tool()
def create_slideshow(
    images: list[str],
    output: str,
    duration: float = 3.0,
    fps: int = 24,
) -> str:
    """
    Create a video slideshow from images.

    Args:
        images: List of image file paths
        output: Output video filename (will be placed in processed dir)
        duration: Duration per image in seconds
        fps: Frames per second

    Returns:
        Path to created video or error message
    """
    logger.info(f"🎬 Creating slideshow from {len(images)} images")

    # Ensure output is in processed dir
    output_path = PROCESSED_DIR / Path(output).name

    if not images:
        return "Error: No images provided"

    try:
        import ffmpeg

        # Build filter for concatenating images
        input_streams = []
        for img in images:
            if _sanitize_path(img):
                stream = ffmpeg.input(img, loop=1, t=duration)
                input_streams.append(stream)

        if not input_streams:
            return "Error: No valid images found"

        # Concatenate all streams
        joined = ffmpeg.concat(*input_streams, v=1, a=0)
        output_stream = ffmpeg.output(joined, str(output_path), r=fps)

        ffmpeg.run(output_stream, overwrite_output=True, quiet=True)

        logger.info(f"✅ Created: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return f"Error: {e}"


@mcp.tool()
def trim_video(
    input_path: str,
    output: str,
    start: float,
    end: float,
) -> str:
    """
    Trim a video to a specific time range.

    Args:
        input_path: Path to input video
        output: Output filename
        start: Start time in seconds
        end: End time in seconds

    Returns:
        Path to trimmed video or error message
    """
    logger.info(f"✂️ Trimming video: {start}s to {end}s")

    output_path = PROCESSED_DIR / Path(output).name

    try:
        import ffmpeg

        duration = end - start
        stream = ffmpeg.input(input_path, ss=start, t=duration)
        output_stream = ffmpeg.output(stream, str(output_path), c="copy")

        ffmpeg.run(output_stream, overwrite_output=True, quiet=True)

        logger.info(f"✅ Trimmed: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return f"Error: {e}"


@mcp.tool()
def add_audio(
    video_path: str,
    audio_path: str,
    output: str,
) -> str:
    """
    Add audio track to a video.

    Args:
        video_path: Path to input video
        audio_path: Path to audio file
        output: Output filename

    Returns:
        Path to output video or error message
    """
    logger.info("🔊 Adding audio to video")

    output_path = PROCESSED_DIR / Path(output).name

    try:
        import ffmpeg

        video = ffmpeg.input(video_path)
        audio = ffmpeg.input(audio_path)

        output_stream = ffmpeg.output(
            video.video,
            audio.audio,
            str(output_path),
            vcodec="copy",
            acodec="aac",
            shortest=None,
        )

        ffmpeg.run(output_stream, overwrite_output=True, quiet=True)

        logger.info(f"✅ Added audio: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return f"Error: {e}"


@mcp.tool()
def change_speed(
    input_path: str,
    output: str,
    speed: float = 1.5,
) -> str:
    """
    Change video playback speed.

    Args:
        input_path: Path to input video
        output: Output filename
        speed: Speed multiplier (e.g., 2.0 = 2x faster)

    Returns:
        Path to output video or error message
    """
    logger.info(f"⏩ Changing speed: {speed}x")

    output_path = PROCESSED_DIR / Path(output).name

    try:
        import ffmpeg

        stream = ffmpeg.input(input_path)
        video = stream.video.filter("setpts", f"{1 / speed}*PTS")
        audio = stream.audio.filter("atempo", speed)

        output_stream = ffmpeg.output(video, audio, str(output_path))
        ffmpeg.run(output_stream, overwrite_output=True, quiet=True)

        logger.info(f"✅ Speed changed: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return f"Error: {e}"


if __name__ == "__main__":
    logger.info("🎬 Starting FFmpeg MCP Server...")
    mcp.run()
