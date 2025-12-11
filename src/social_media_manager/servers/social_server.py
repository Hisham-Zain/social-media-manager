#!/usr/bin/env python3
"""
Social Media MCP Server

A local FOSS MCP server wrapping social media APIs.
Cost: $0 - Uses instagrapi (unofficial Instagram API).

This isolates the fragile social API logic from your main application.
If an API breaks, only this server needs updating.
"""

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Social Media Publisher")

# Credentials from environment
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")


def _get_instagram_client():
    """Get authenticated Instagram client."""
    try:
        from instagrapi import Client

        if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
            raise ValueError("Instagram credentials not configured")

        cl = Client()
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        logger.info(f"📸 Logged into Instagram as {INSTAGRAM_USERNAME}")
        return cl

    except Exception as e:
        logger.error(f"Instagram login error: {e}")
        raise


@mcp.tool()
def post_to_instagram(
    caption: str,
    media_path: str,
    media_type: str = "auto",
) -> str:
    """
    Post content to Instagram.

    Args:
        caption: Post caption with hashtags
        media_path: Path to image or video file
        media_type: 'photo', 'video', 'reel', or 'auto' (detect from extension)

    Returns:
        Post ID on success, error message on failure
    """
    logger.info(f"📤 Posting to Instagram: {media_path}")

    try:
        cl = _get_instagram_client()
        path = Path(media_path)

        if not path.exists():
            return f"Error: File not found: {media_path}"

        # Auto-detect media type
        if media_type == "auto":
            ext = path.suffix.lower()
            if ext in [".mp4", ".mov", ".avi"]:
                media_type = "reel"
            else:
                media_type = "photo"

        # Upload based on type
        if media_type == "photo":
            media = cl.photo_upload(str(path), caption)
        elif media_type in ["video", "reel"]:
            media = cl.clip_upload(str(path), caption)
        else:
            return f"Error: Unknown media type: {media_type}"

        if media:
            logger.info(f"✅ Posted! ID: {media.pk}")
            return f"Success! Post ID: {media.pk}"
        else:
            return "Error: Upload returned None"

    except Exception as e:
        logger.error(f"Instagram post error: {e}")
        return f"Error: {e}"


@mcp.tool()
def post_story(
    media_path: str,
    caption: str = "",
) -> str:
    """
    Post a story to Instagram.

    Args:
        media_path: Path to image or video
        caption: Optional story caption

    Returns:
        Story ID on success
    """
    logger.info(f"📖 Posting story: {media_path}")

    try:
        cl = _get_instagram_client()
        path = Path(media_path)

        if not path.exists():
            return f"Error: File not found: {media_path}"

        ext = path.suffix.lower()
        if ext in [".mp4", ".mov"]:
            story = cl.video_upload_to_story(str(path), caption)
        else:
            story = cl.photo_upload_to_story(str(path), caption)

        if story:
            logger.info(f"✅ Story posted! ID: {story.pk}")
            return f"Success! Story ID: {story.pk}"
        else:
            return "Error: Story upload returned None"

    except Exception as e:
        logger.error(f"Story post error: {e}")
        return f"Error: {e}"


@mcp.tool()
def get_profile_info(username: str = "") -> str:
    """
    Get Instagram profile information.

    Args:
        username: Username to lookup (default: own profile)

    Returns:
        Profile information as JSON
    """
    try:
        cl = _get_instagram_client()

        if username:
            user = cl.user_info_by_username(username)
        else:
            user = cl.user_info(cl.user_id)

        info = {
            "username": user.username,
            "full_name": user.full_name,
            "followers": user.follower_count,
            "following": user.following_count,
            "posts": user.media_count,
            "bio": user.biography,
        }

        return str(info)

    except Exception as e:
        logger.error(f"Profile lookup error: {e}")
        return f"Error: {e}"


@mcp.tool()
def check_credentials() -> str:
    """
    Check if Instagram credentials are configured and valid.

    Returns:
        Status message
    """
    if not INSTAGRAM_USERNAME:
        return "Error: INSTAGRAM_USERNAME not set in environment"
    if not INSTAGRAM_PASSWORD:
        return "Error: INSTAGRAM_PASSWORD not set in environment"

    try:
        cl = _get_instagram_client()
        return f"Success! Logged in as {INSTAGRAM_USERNAME}"
    except Exception as e:
        return f"Error: Login failed - {e}"


if __name__ == "__main__":
    logger.info("📱 Starting Social Media MCP Server...")
    mcp.run()
