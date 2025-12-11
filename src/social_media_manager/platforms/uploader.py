import logging
from typing import Any

import requests

from ..config import config
from ..database import DatabaseManager

logger = logging.getLogger(__name__)


class PlatformUploader:
    """
    Handles uploading content to social platforms.
    """

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db if db else DatabaseManager()
        self.creds_dir = config.CREDS_DIR

    def upload(
        self,
        platform: str,
        data: dict[str, Any],
        client_config: dict[str, Any] | None = None,
    ) -> str | bool | None:
        if not client_config:
            client_config = {}
        platform = platform.lower()

        logger.info(
            f"📤 Uploading to {platform} for {client_config.get('niche', 'Unknown')}..."
        )

        if platform == "youtube":
            return self._upload_youtube(data, client_config)
        elif platform == "facebook":
            return self._upload_facebook(data, client_config)
        elif platform == "instagram":
            return self._upload_instagram(data, client_config)
        elif platform == "tiktok":
            return self._upload_tiktok(data, client_config)
        else:
            return self._notify_ready(platform, data)

    def _notify_ready(self, platform: str, data: dict[str, Any]) -> bool:
        logger.info(f"✅ {platform.upper()} READY - Manual Upload Required.")
        logger.info(f"File: {data.get('path')}")
        return True

    def _upload_instagram(
        self, data: dict[str, Any], client_config: dict[str, Any]
    ) -> str | None:
        creds = client_config.get("platforms", {}).get("instagram", {})
        username = (
            creds.get("username") or config.INSTAGRAM_ACCOUNT_ID
        )  # fallback if stored in env
        password = creds.get("password")

        if not username or not password:
            return self._notify_ready("instagram (No Credentials)", data)  # type: ignore

        try:
            from instagrapi import Client

            cl = Client()
            cl.login(username, password)
            logger.info(f"📸 Logged in as {username}")

            media = cl.clip_upload(data["path"], caption=data["caption"])
            if media:
                self.db.log_upload(data["id"], "instagram", str(media.pk))
                return str(media.pk)
        except ImportError:
            logger.error(
                "❌ IG Upload Error: 'instagrapi' not installed. Run: pip install instagrapi"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ IG Network Error: {e}")
            return None
        except KeyError as e:
            logger.error(f"❌ IG Upload Error: Missing required data key: {e}")
            return None
        except Exception as e:
            # Catch login failures and other API errors
            error_str = str(e).lower()
            if (
                "login" in error_str
                or "credential" in error_str
                or "password" in error_str
            ):
                logger.error("❌ IG Auth Error: Login failed. Check credentials.")
            else:
                logger.error(f"❌ IG Upload Error ({type(e).__name__}): {e}")
            return None
        return None

    def _upload_facebook(
        self, data: dict[str, Any], client_config: dict[str, Any]
    ) -> str | None:
        creds = client_config.get("platforms", {}).get("facebook", {})
        page_id = creds.get("page_id") or config.FACEBOOK_PAGE_ID
        token = creds.get("token") or config.META_ACCESS_TOKEN

        if not page_id or not token:
            return self._notify_ready("facebook (No Credentials)", data)  # type: ignore

        url = f"https://graph-video.facebook.com/v19.0/{page_id}/videos"
        try:
            with open(data["path"], "rb") as f:
                resp = requests.post(
                    url,
                    params={"access_token": token, "description": data["caption"]},
                    files={"source": f},
                    timeout=60,
                )
            if resp.status_code == 200:
                vid_id = resp.json().get("id")
                self.db.log_upload(data["id"], "facebook", vid_id)
                return vid_id
            else:
                logger.error(f"❌ FB API Error: {resp.text}")
        except FileNotFoundError as e:
            logger.error(f"❌ FB Upload Error: Video file not found: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ FB Network Error: Could not connect to Facebook API: {e}")
        except requests.exceptions.Timeout:
            logger.error("❌ FB Upload Error: Request timed out after 60s")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ FB Upload Error ({type(e).__name__}): {e}")
        except KeyError as e:
            logger.error(f"❌ FB Upload Error: Missing required data key: {e}")
        return None

    def _upload_youtube(
        self, data: dict[str, Any], client_config: dict[str, Any]
    ) -> bool | None:
        # YouTube auth is complex (OAuth flow). Keeping simplified for now.
        return self._notify_ready("youtube", data)

    def _upload_tiktok(
        self, data: dict[str, Any], client_config: dict[str, Any]
    ) -> bool | None:
        # TikTok requires unofficial API or manual upload
        return self._notify_ready("tiktok", data)

    # === MCP-BASED METHODS ===

    async def upload_with_mcp(
        self,
        content: dict[str, Any],
        platforms: list[str],
    ) -> dict[str, bool]:
        """
        Upload to multiple platforms via Social Media Sync MCP.

        This enables unified multi-platform posting through a single
        MCP server that handles platform-specific APIs.

        Args:
            content: Content data with keys:
                - path: Path to video/image file
                - caption: Post caption
                - hashtags: Optional list of hashtags
            platforms: List of platforms (instagram, tiktok, youtube, etc.)

        Returns:
            Dict mapping platform to success status
        """
        results: dict[str, bool] = {}

        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "social-media" not in manager.servers:
                logger.debug("Social Media MCP not configured, using direct upload")
                # Fall back to direct upload for each platform
                for platform in platforms:
                    try:
                        result = self.upload(platform, content)
                        results[platform] = bool(result)
                    except Exception as e:
                        logger.error(f"Direct upload to {platform} failed: {e}")
                        results[platform] = False
                return results

            logger.info(f"📤 MCP Upload: {len(platforms)} platforms...")

            result = await manager.call_tool(
                "social-media",
                "post_content",
                {
                    "content": content.get("caption", ""),
                    "media_path": content.get("path"),
                    "platforms": platforms,
                    "hashtags": content.get("hashtags", []),
                },
            )

            if "error" in result:
                logger.warning(f"MCP upload failed: {result['error']}")
                # Fallback to individual uploads
                for platform in platforms:
                    try:
                        res = self.upload(platform, content)
                        results[platform] = bool(res)
                    except Exception:
                        results[platform] = False
            else:
                # Parse MCP response
                mcp_results = result.get("result", {})
                for platform in platforms:
                    results[platform] = mcp_results.get(platform, False)

            return results

        except ImportError:
            logger.debug("MCP client not available")
            for platform in platforms:
                results[platform] = False
            return results
        except Exception as e:
            logger.error(f"MCP upload error: {e}")
            for platform in platforms:
                results[platform] = False
            return results

    async def schedule_with_mcp(
        self,
        content: dict[str, Any],
        platforms: list[str],
        schedule_time: str,
    ) -> dict[str, bool]:
        """
        Schedule content for future posting via MCP.

        Args:
            content: Content data
            platforms: Target platforms
            schedule_time: ISO format datetime for posting

        Returns:
            Dict mapping platform to scheduling success
        """
        results: dict[str, bool] = {}

        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "social-media" not in manager.servers:
                logger.warning("Social Media MCP not available for scheduling")
                for platform in platforms:
                    results[platform] = False
                return results

            result = await manager.call_tool(
                "social-media",
                "schedule_post",
                {
                    "content": content.get("caption", ""),
                    "media_path": content.get("path"),
                    "platforms": platforms,
                    "schedule_time": schedule_time,
                },
            )

            if "error" in result:
                logger.error(f"Scheduling failed: {result['error']}")
                for platform in platforms:
                    results[platform] = False
            else:
                mcp_results = result.get("result", {})
                for platform in platforms:
                    results[platform] = mcp_results.get(platform, False)

            return results

        except Exception as e:
            logger.error(f"MCP scheduling error: {e}")
            for platform in platforms:
                results[platform] = False
            return results
