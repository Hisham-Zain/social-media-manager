"""
Stock Hunter Pro - Multi-source stock media finder.

Sources:
1. Pexels (Primary) - High quality, API key required
2. Pixabay (Fallback) - Free API with high limits
3. Coverr (Fallback) - Web scraping, free for commercial use

Searches sources in order until a match is found.
"""

import hashlib
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

import requests
from loguru import logger

from ..config import config


@dataclass
class StockResult:
    """Result from a stock media search."""

    source: str
    query: str
    video_id: str
    url: str
    preview_url: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    author: str | None = None
    downloaded_path: str | None = None


class StockHunter:
    """
    Multi-source stock media hunter.

    Searches multiple sources in order:
    1. Pexels (if API key available)
    2. Pixabay (if API key available)
    3. Coverr (free, web scraping)

    Example:
        hunter = StockHunter()

        # Hunt for stock video
        path = hunter.hunt("sunset beach")

        # Hunt with specific source
        path = hunter.hunt("coffee shop", source="pixabay")

        # Search without downloading
        results = hunter.search("nature", per_page=10)
    """

    PEXELS_API = "https://api.pexels.com/videos/search"
    PIXABAY_API = "https://pixabay.com/api/videos/"
    COVERR_SEARCH = "https://coverr.co/s?q="

    def __init__(self) -> None:
        self.pexels_key: str = config.PEXELS_API_KEY
        self.pixabay_key: str = getattr(config, "PIXABAY_API_KEY", "") or ""
        self.download_dir: Path = config.STOCK_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Track available sources
        self.sources: list[str] = []
        if self.pexels_key:
            self.sources.append("pexels")
        if self.pixabay_key:
            self.sources.append("pixabay")
        self.sources.append("coverr")  # Always available (web scraping)

        logger.info(
            f"🦅 StockHunter Pro initialized (sources: {', '.join(self.sources)})"
        )

    def hunt(
        self,
        query: str,
        source: Literal["auto", "pexels", "pixabay", "coverr"] = "auto",
        orientation: Literal["landscape", "portrait", "square"] = "portrait",
        min_duration: int = 0,
        max_duration: int = 60,
    ) -> str | None:
        """
        Search and download a stock video matching the query.

        Args:
            query: Search query.
            source: Specific source or "auto" for fallback chain.
            orientation: Video orientation preference.
            min_duration: Minimum duration in seconds.
            max_duration: Maximum duration in seconds.

        Returns:
            Path to downloaded video, or None if not found.
        """
        if source == "auto":
            # Try sources in order
            for src in self.sources:
                result = self._hunt_from_source(
                    query, src, orientation, min_duration, max_duration
                )
                if result:
                    return result

            logger.warning(f"🦅 No stock found for '{query}' in any source")
            return None
        else:
            return self._hunt_from_source(
                query, source, orientation, min_duration, max_duration
            )

    def _hunt_from_source(
        self,
        query: str,
        source: str,
        orientation: str,
        min_duration: int,
        max_duration: int,
    ) -> str | None:
        """Hunt from a specific source."""
        logger.info(f"🦅 Searching {source.upper()} for '{query}'...")

        try:
            if source == "pexels":
                return self._hunt_pexels(query, orientation, min_duration, max_duration)
            elif source == "pixabay":
                return self._hunt_pixabay(
                    query, orientation, min_duration, max_duration
                )
            elif source == "coverr":
                return self._hunt_coverr(query)
        except Exception as e:
            logger.warning(f"⚠️ {source} search failed: {e}")

        return None

    def _hunt_pexels(
        self,
        query: str,
        orientation: str,
        min_duration: int,
        max_duration: int,
    ) -> str | None:
        """Search Pexels for stock video."""
        if not self.pexels_key:
            return None

        headers = {"Authorization": self.pexels_key}
        params = {
            "query": query,
            "per_page": 5,
            "orientation": orientation,
        }

        res = requests.get(self.PEXELS_API, headers=headers, params=params, timeout=10)
        res.raise_for_status()

        data = res.json()
        videos = data.get("videos", [])

        # Filter by duration
        filtered = [
            v for v in videos if min_duration <= v.get("duration", 0) <= max_duration
        ]

        if not filtered:
            if videos:
                logger.info(
                    f"⚠️ Pexels: {len(videos)} videos, none matched duration filter"
                )
            return None

        # Select random video
        video = random.choice(filtered)
        video_files = video.get("video_files", [])

        # Prefer HD
        best_file = next(
            (v for v in video_files if v.get("width", 0) >= 720),
            video_files[0] if video_files else None,
        )

        if not best_file:
            return None

        # Download
        return self._download(
            url=best_file["link"], filename=f"pexels_{video['id']}.mp4", source="pexels"
        )

    def _hunt_pixabay(
        self,
        query: str,
        orientation: str,
        min_duration: int,
        max_duration: int,
    ) -> str | None:
        """Search Pixabay for stock video."""
        if not self.pixabay_key:
            return None

        # Map orientation
        pixabay_orientation = {
            "landscape": "horizontal",
            "portrait": "vertical",
            "square": "all",
        }.get(orientation, "all")

        params = {
            "key": self.pixabay_key,
            "q": query,
            "video_type": "film",
            "per_page": 5,
            "safesearch": "true",
        }

        res = requests.get(self.PIXABAY_API, params=params, timeout=10)
        res.raise_for_status()

        data = res.json()
        videos = data.get("hits", [])

        # Filter by duration
        filtered = [
            v for v in videos if min_duration <= v.get("duration", 0) <= max_duration
        ]

        if not filtered:
            return None

        # Select random video
        video = random.choice(filtered)

        # Get video URL (prefer large, then medium)
        video_data = video.get("videos", {})
        video_url = None

        for quality in ["large", "medium", "small", "tiny"]:
            if quality in video_data and video_data[quality].get("url"):
                video_url = video_data[quality]["url"]
                break

        if not video_url:
            return None

        # Download
        return self._download(
            url=video_url, filename=f"pixabay_{video['id']}.mp4", source="pixabay"
        )

    def _hunt_coverr(self, query: str) -> str | None:
        """Search Coverr for stock video (web scraping)."""
        # Coverr doesn't have an official API, so we scrape
        search_url = f"{self.COVERR_SEARCH}{quote_plus(query)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            res = requests.get(search_url, headers=headers, timeout=10)
            res.raise_for_status()
            html = res.text

            # Extract video URLs from page
            # Coverr uses various patterns, try to find download links
            video_patterns = [
                r'href="(/videos/[^"]+)"',
                r'"downloadUrl":"([^"]+)"',
                r'data-video-url="([^"]+)"',
            ]

            video_pages = []
            for pattern in video_patterns:
                matches = re.findall(pattern, html)
                video_pages.extend(matches)

            if not video_pages:
                return None

            # Get a random video page
            video_path = random.choice(video_pages[:5])

            # If it's a relative URL, make it absolute
            if video_path.startswith("/"):
                video_url = f"https://coverr.co{video_path}"
            else:
                video_url = video_path

            # Try to get the actual video file
            if "/videos/" in video_url and not video_url.endswith(".mp4"):
                # Need to visit the page to get download URL
                video_res = requests.get(video_url, headers=headers, timeout=10)
                video_html = video_res.text

                # Find download URL
                download_match = re.search(r'"downloadUrl":"([^"]+)"', video_html)
                if download_match:
                    video_url = download_match.group(1)
                else:
                    # Try finding direct video link
                    mp4_match = re.search(r'(https://[^"]+\.mp4)', video_html)
                    if mp4_match:
                        video_url = mp4_match.group(1)
                    else:
                        return None

            # Generate filename from URL
            video_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
            filename = f"coverr_{video_hash}.mp4"

            return self._download(url=video_url, filename=filename, source="coverr")

        except Exception as e:
            logger.warning(f"Coverr search failed: {e}")
            return None

    def _download(self, url: str, filename: str, source: str) -> str | None:
        """Download a video file."""
        path = self.download_dir / filename

        if path.exists() and path.stat().st_size > 0:
            logger.info(f"✅ Using cached: {filename}")
            return str(path)

        try:
            logger.info(f"⬇️ Downloading from {source}: {filename}...")

            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()

                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            if path.exists() and path.stat().st_size > 0:
                logger.info(
                    f"✅ Downloaded: {filename} ({path.stat().st_size // 1024}KB)"
                )
                return str(path)
            else:
                logger.error("❌ Download failed: empty file")
                return None

        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            if path.exists():
                path.unlink()
            return None

    def search(
        self,
        query: str,
        source: Literal["pexels", "pixabay", "all"] = "all",
        per_page: int = 10,
    ) -> list[StockResult]:
        """
        Search for stock videos without downloading.

        Args:
            query: Search query.
            source: Which source to search.
            per_page: Number of results per source.

        Returns:
            List of StockResult objects.
        """
        results = []

        if source in ("pexels", "all") and self.pexels_key:
            results.extend(self._search_pexels(query, per_page))

        if source in ("pixabay", "all") and self.pixabay_key:
            results.extend(self._search_pixabay(query, per_page))

        return results

    def _search_pexels(self, query: str, per_page: int) -> list[StockResult]:
        """Search Pexels and return results."""
        results = []

        try:
            headers = {"Authorization": self.pexels_key}
            params = {"query": query, "per_page": per_page}

            res = requests.get(
                self.PEXELS_API, headers=headers, params=params, timeout=10
            )
            res.raise_for_status()

            for video in res.json().get("videos", []):
                video_files = video.get("video_files", [])
                best_file = next(
                    (v for v in video_files if v.get("width", 0) >= 720),
                    video_files[0] if video_files else None,
                )

                if best_file:
                    results.append(
                        StockResult(
                            source="pexels",
                            query=query,
                            video_id=str(video["id"]),
                            url=best_file["link"],
                            preview_url=video.get("image"),
                            duration=video.get("duration"),
                            width=best_file.get("width"),
                            height=best_file.get("height"),
                            author=video.get("user", {}).get("name"),
                        )
                    )

        except Exception as e:
            logger.warning(f"Pexels search error: {e}")

        return results

    def _search_pixabay(self, query: str, per_page: int) -> list[StockResult]:
        """Search Pixabay and return results."""
        results = []

        try:
            params = {
                "key": self.pixabay_key,
                "q": query,
                "video_type": "film",
                "per_page": per_page,
            }

            res = requests.get(self.PIXABAY_API, params=params, timeout=10)
            res.raise_for_status()

            for video in res.json().get("hits", []):
                video_data = video.get("videos", {})
                video_url = None
                width = height = None

                for quality in ["large", "medium", "small"]:
                    if quality in video_data and video_data[quality].get("url"):
                        video_url = video_data[quality]["url"]
                        width = video_data[quality].get("width")
                        height = video_data[quality].get("height")
                        break

                if video_url:
                    results.append(
                        StockResult(
                            source="pixabay",
                            query=query,
                            video_id=str(video["id"]),
                            url=video_url,
                            preview_url=f"https://i.vimeocdn.com/video/{video['picture_id']}_640x360.jpg",
                            duration=video.get("duration"),
                            width=width,
                            height=height,
                            author=video.get("user"),
                        )
                    )

        except Exception as e:
            logger.warning(f"Pixabay search error: {e}")

        return results

    def hunt_images(
        self,
        query: str,
        source: Literal["auto", "pexels", "pixabay"] = "auto",
        orientation: str = "landscape",
    ) -> str | None:
        """
        Search and download a stock image.

        Args:
            query: Search query.
            source: Specific source or "auto".
            orientation: Image orientation.

        Returns:
            Path to downloaded image, or None.
        """
        if source == "auto":
            sources = [s for s in self.sources if s != "coverr"]
        else:
            sources = [source]

        for src in sources:
            try:
                if src == "pexels":
                    result = self._hunt_pexels_image(query, orientation)
                elif src == "pixabay":
                    result = self._hunt_pixabay_image(query, orientation)
                else:
                    continue

                if result:
                    return result

            except Exception as e:
                logger.warning(f"Image hunt from {src} failed: {e}")

        return None

    def _hunt_pexels_image(self, query: str, orientation: str) -> str | None:
        """Search Pexels for stock image."""
        if not self.pexels_key:
            return None

        headers = {"Authorization": self.pexels_key}
        params = {"query": query, "per_page": 5, "orientation": orientation}

        res = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params,
            timeout=10,
        )
        res.raise_for_status()

        photos = res.json().get("photos", [])
        if not photos:
            return None

        photo = random.choice(photos)
        image_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get(
            "original"
        )

        if not image_url:
            return None

        filename = f"pexels_img_{photo['id']}.jpg"
        return self._download(image_url, filename, "pexels")

    def _hunt_pixabay_image(self, query: str, orientation: str) -> str | None:
        """Search Pixabay for stock image."""
        if not self.pixabay_key:
            return None

        params = {
            "key": self.pixabay_key,
            "q": query,
            "per_page": 5,
            "orientation": orientation,
            "safesearch": "true",
        }

        res = requests.get("https://pixabay.com/api/", params=params, timeout=10)
        res.raise_for_status()

        photos = res.json().get("hits", [])
        if not photos:
            return None

        photo = random.choice(photos)
        image_url = photo.get("largeImageURL") or photo.get("webformatURL")

        if not image_url:
            return None

        filename = f"pixabay_img_{photo['id']}.jpg"
        return self._download(image_url, filename, "pixabay")


# Convenience function
def hunt_stock(query: str, media_type: str = "video") -> str | None:
    """Quick function to hunt for stock media."""
    hunter = StockHunter()
    if media_type == "image":
        return hunter.hunt_images(query)
    return hunter.hunt(query)
