"""
Asset Factory - Produces platform-native assets from AI analysis.

Transforms ContentAlchemist output into actual deliverables:
- LinkedIn carousels (Pillow images)
- Video clips (VideoProcessor subclips)
- Quote graphics
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from loguru import logger

from ..config import config


@dataclass
class GeneratedAsset:
    """A generated asset file."""

    asset_type: str
    file_path: str
    platform: str
    metadata: dict


class AssetFactory:
    """
    Factory for generating platform-native assets.

    Takes specifications from ContentAlchemist and produces
    actual files: images, video clips, text files.

    Example:
        factory = AssetFactory()
        assets = factory.build_carousel(["Slide 1", "Slide 2", "Slide 3"])
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or config.PROCESSED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Carousel template settings
        self.carousel_size = (1080, 1350)  # Instagram/LinkedIn carousel
        self.carousel_bg_color = (30, 30, 40)
        self.carousel_text_color = (255, 255, 255)
        self.carousel_accent_color = (100, 150, 255)

    def build_carousel(
        self,
        slides: list[str],
        title: str = "carousel",
        style: Literal["minimal", "bold", "gradient"] = "bold",
    ) -> list[GeneratedAsset]:
        """
        Build LinkedIn carousel images from slide texts.

        Args:
            slides: List of text content for each slide.
            title: Base name for output files.
            style: Visual style preset.

        Returns:
            List of GeneratedAsset with image paths.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.error("Pillow not installed. Run: pip install Pillow")
            return []

        logger.info(f"🎨 Building carousel: {len(slides)} slides")
        assets = []

        for i, text in enumerate(slides):
            # Create image
            img = Image.new("RGB", self.carousel_size, self.carousel_bg_color)
            draw = ImageDraw.Draw(img)

            # Apply style
            if style == "gradient":
                self._apply_gradient(img)
            elif style == "bold":
                self._apply_bold_style(draw)

            # Draw slide number
            slide_num = f"{i + 1}/{len(slides)}"
            draw.text(
                (50, 50),
                slide_num,
                fill=self.carousel_accent_color,
                font=self._get_font(24),
            )

            # Draw main text (centered, wrapped)
            self._draw_centered_text(draw, text, self.carousel_size, self._get_font(48))

            # Save
            filename = f"{title}_slide_{i + 1}.png"
            filepath = self.output_dir / filename
            img.save(str(filepath))

            assets.append(
                GeneratedAsset(
                    asset_type="linkedin_carousel",
                    file_path=str(filepath),
                    platform="linkedin",
                    metadata={"slide_number": i + 1, "text": text},
                )
            )

        logger.info(f"✅ Carousel complete: {len(assets)} slides saved")
        return assets

    def _apply_gradient(self, img) -> None:
        """Apply a gradient background."""
        try:
            width, height = img.size
            for y in range(height):
                r = int(30 + (y / height) * 20)
                g = int(30 + (y / height) * 30)
                b = int(50 + (y / height) * 40)
                for x in range(width):
                    img.putpixel((x, y), (r, g, b))
        except Exception:
            pass

    def _apply_bold_style(self, draw) -> None:
        """Apply bold style accents."""
        # Draw accent line at top
        draw.rectangle(
            [(0, 0), (self.carousel_size[0], 8)],
            fill=self.carousel_accent_color,
        )

    def _get_font(self, size: int):
        """Get a font, falling back to default if needed."""
        try:
            from PIL import ImageFont

            # Try common system fonts
            for font_name in ["DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttf"]:
                try:
                    return ImageFont.truetype(font_name, size)
                except OSError:
                    continue
            return ImageFont.load_default()
        except Exception:
            from PIL import ImageFont

            return ImageFont.load_default()

    def _draw_centered_text(self, draw, text: str, size: tuple, font) -> None:
        """Draw text centered and wrapped."""
        width, height = size
        max_chars = 25  # Characters per line

        # Word wrap
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if len(test_line) <= max_chars:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Calculate vertical position
        line_height = 60
        total_height = len(lines) * line_height
        start_y = (height - total_height) // 2

        # Draw each line
        for i, line in enumerate(lines):
            y = start_y + (i * line_height)
            # Get text bbox for centering
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                text_width = len(line) * 20  # Fallback estimate

            x = (width - text_width) // 2
            draw.text((x, y), line, fill=self.carousel_text_color, font=font)

    def extract_clips(
        self,
        video_path: str,
        timestamps: list[tuple[float, float]],
        prefix: str = "clip",
    ) -> list[GeneratedAsset]:
        """
        Extract video clips at specified timestamps.

        Args:
            video_path: Path to source video.
            timestamps: List of (start, end) tuples in seconds.
            prefix: Filename prefix for clips.

        Returns:
            List of GeneratedAsset with clip paths.
        """
        from ..core.processor import VideoProcessor

        logger.info(
            f"✂️ Extracting {len(timestamps)} clips from {Path(video_path).name}"
        )
        processor = VideoProcessor()
        assets = []

        for i, (start, end) in enumerate(timestamps):
            try:
                output_path = str(self.output_dir / f"{prefix}_{i + 1}.mp4")

                # Use processor's subclip capability
                from moviepy import VideoFileClip

                with VideoFileClip(video_path) as clip:
                    subclip = clip.subclip(start, min(end, clip.duration))
                    subclip.write_videofile(
                        output_path,
                        codec="libx264",
                        audio_codec="aac",
                        logger=None,
                    )

                assets.append(
                    GeneratedAsset(
                        asset_type="video_clip",
                        file_path=output_path,
                        platform="tiktok",
                        metadata={"start": start, "end": end, "duration": end - start},
                    )
                )

            except Exception as e:
                logger.error(f"Failed to extract clip {i + 1}: {e}")

        logger.info(f"✅ Extracted {len(assets)} clips")
        return assets

    def build_quote_graphic(
        self,
        quote: str,
        author: str = "",
        style: Literal["dark", "light", "vibrant"] = "dark",
    ) -> GeneratedAsset | None:
        """
        Build a shareable quote graphic.

        Args:
            quote: The quote text.
            author: Attribution (optional).
            style: Visual style.

        Returns:
            GeneratedAsset with image path.
        """
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            logger.error("Pillow not installed")
            return None

        logger.info("🎨 Building quote graphic")

        # Square format for Instagram
        size = (1080, 1080)
        bg_colors = {
            "dark": (20, 20, 30),
            "light": (245, 245, 250),
            "vibrant": (100, 50, 150),
        }
        text_colors = {
            "dark": (255, 255, 255),
            "light": (30, 30, 40),
            "vibrant": (255, 255, 255),
        }

        img = Image.new("RGB", size, bg_colors.get(style, bg_colors["dark"]))
        draw = ImageDraw.Draw(img)

        # Draw quote marks
        draw.text(
            (80, 200),
            '"',
            fill=(100, 100, 120),
            font=self._get_font(120),
        )

        # Draw quote
        self._draw_centered_text(draw, quote, size, self._get_font(42))

        # Draw author
        if author:
            draw.text(
                (size[0] // 2 - 100, size[1] - 150),
                f"— {author}",
                fill=text_colors.get(style, text_colors["dark"]),
                font=self._get_font(28),
            )

        # Save
        filepath = self.output_dir / f"quote_{hash(quote) % 10000}.png"
        img.save(str(filepath))

        return GeneratedAsset(
            asset_type="quote_graphic",
            file_path=str(filepath),
            platform="instagram",
            metadata={"quote": quote, "author": author},
        )

    def save_twitter_thread(
        self, tweets: list[str], title: str = "thread"
    ) -> GeneratedAsset:
        """
        Save a Twitter thread as a text file.

        Args:
            tweets: List of tweet texts.
            title: Base filename.

        Returns:
            GeneratedAsset with file path.
        """
        logger.info(f"💬 Saving Twitter thread: {len(tweets)} tweets")

        content = "TWITTER THREAD\n" + "=" * 40 + "\n\n"
        for i, tweet in enumerate(tweets, 1):
            content += f"Tweet {i}:\n{tweet}\n"
            content += f"[{len(tweet)}/280 chars]\n\n"

        filepath = self.output_dir / f"{title}_thread.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return GeneratedAsset(
            asset_type="twitter_thread",
            file_path=str(filepath),
            platform="twitter",
            metadata={"tweet_count": len(tweets)},
        )
