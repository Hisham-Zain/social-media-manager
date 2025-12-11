"""
Background Removal Module for AgencyOS.

AI-powered background removal using Rembg (U2-Net).
Optimized for RTX 2060 (6GB VRAM) - also works great on CPU.
"""

import time
from pathlib import Path
from typing import Literal

from loguru import logger
from PIL import Image

from ..config import config

# Lazy import rembg to avoid loading model until needed
REMBG_AVAILABLE = False
try:
    from rembg import new_session, remove

    REMBG_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Rembg not installed. Run: pip install rembg")


class BackgroundRemover:
    """
    AI Background Removal using Rembg.

    Supports multiple models optimized for different use cases:
    - u2net: General purpose (default)
    - u2netp: Lightweight/fast
    - u2net_human_seg: Optimized for people
    - isnet-general-use: High quality
    """

    # Available models and their use cases
    MODELS = {
        "u2net": "General purpose (balanced)",
        "u2netp": "Fast/lightweight",
        "u2net_human_seg": "People/portraits",
        "u2net_cloth_seg": "Clothing segmentation",
        "isnet-general-use": "High quality general",
        "isnet-anime": "Anime/illustrations",
        "silueta": "Fast silhouette",
    }

    def __init__(
        self,
        model: Literal[
            "u2net", "u2netp", "u2net_human_seg", "isnet-general-use"
        ] = "u2net",
    ) -> None:
        """
        Initialize BackgroundRemover.

        Args:
            model: Model to use for background removal.
        """
        self.model_name = model
        self.session = None
        self.output_dir = Path(config.PROCESSED_DIR) / "nobg"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not REMBG_AVAILABLE:
            logger.error("❌ Rembg not available. Install with: pip install rembg")

    def _load_session(self) -> None:
        """Lazy load the model session."""
        if self.session is None and REMBG_AVAILABLE:
            logger.info(f"🔄 Loading Rembg model: {self.model_name}")
            self.session = new_session(self.model_name)
            logger.info("✅ Rembg model loaded")

    def remove_background(
        self,
        image_path: str,
        output_path: str | None = None,
        alpha_matting: bool = False,
        only_mask: bool = False,
    ) -> str | None:
        """
        Remove background from an image.

        Args:
            image_path: Path to input image.
            output_path: Optional output path. Auto-generated if not provided.
            alpha_matting: Use alpha matting for better edges (slower).
            only_mask: Return only the mask instead of the image.

        Returns:
            Path to the output image with transparent background.
        """
        if not REMBG_AVAILABLE:
            logger.error("❌ Rembg not available")
            return None

        try:
            self._load_session()

            # Load input image
            input_path = Path(image_path)
            if not input_path.exists():
                logger.error(f"❌ Image not found: {image_path}")
                return None

            logger.info(f"🎨 Removing background: {input_path.name}")
            start_time = time.time()

            # Read image
            with open(input_path, "rb") as f:
                input_data = f.read()

            # Remove background
            output_data = remove(
                input_data,
                session=self.session,
                alpha_matting=alpha_matting,
                only_mask=only_mask,
            )

            # Determine output path
            if output_path is None:
                suffix = "_mask" if only_mask else "_nobg"
                output_path = self.output_dir / f"{input_path.stem}{suffix}.png"
            else:
                output_path = Path(output_path)

            # Save result
            with open(output_path, "wb") as f:
                f.write(output_data)

            elapsed = time.time() - start_time
            logger.info(f"✅ Background removed in {elapsed:.1f}s → {output_path.name}")

            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Background removal failed: {e}")
            return None

    def remove_background_pil(
        self,
        image: Image.Image,
        alpha_matting: bool = False,
    ) -> Image.Image | None:
        """
        Remove background from a PIL Image object.

        Args:
            image: PIL Image object.
            alpha_matting: Use alpha matting for better edges.

        Returns:
            PIL Image with transparent background.
        """
        if not REMBG_AVAILABLE:
            return None

        try:
            self._load_session()
            return remove(image, session=self.session, alpha_matting=alpha_matting)
        except Exception as e:
            logger.error(f"❌ Background removal failed: {e}")
            return None

    def batch_remove(
        self,
        image_paths: list[str],
        output_dir: str | None = None,
    ) -> list[str]:
        """
        Remove backgrounds from multiple images.

        Args:
            image_paths: List of input image paths.
            output_dir: Output directory for processed images.

        Returns:
            List of output image paths.
        """
        if not REMBG_AVAILABLE:
            return []

        self._load_session()  # Load once for batch

        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for i, img_path in enumerate(image_paths):
            logger.info(
                f"📸 Processing {i + 1}/{len(image_paths)}: {Path(img_path).name}"
            )
            output = self.remove_background(
                img_path, output_path=str(out_dir / f"{Path(img_path).stem}_nobg.png")
            )
            if output:
                results.append(output)

        logger.info(f"✅ Batch complete: {len(results)}/{len(image_paths)} processed")
        return results

    def create_composite(
        self,
        foreground_path: str,
        background_path: str,
        output_path: str | None = None,
    ) -> str | None:
        """
        Remove background from foreground and composite onto new background.

        Args:
            foreground_path: Image to extract subject from.
            background_path: New background image.
            output_path: Output path for composite.

        Returns:
            Path to composite image.
        """
        try:
            # Remove background from foreground
            fg_nobg = self.remove_background_pil(
                Image.open(foreground_path).convert("RGBA")
            )
            if fg_nobg is None:
                return None

            # Load and resize background
            bg = Image.open(background_path).convert("RGBA")
            bg = bg.resize(fg_nobg.size)

            # Composite
            composite = Image.alpha_composite(bg, fg_nobg)

            # Save
            if output_path is None:
                output_path = self.output_dir / f"composite_{int(time.time())}.png"

            composite.save(output_path)
            logger.info(f"✅ Composite created: {output_path}")

            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Composite creation failed: {e}")
            return None

    def unload(self) -> None:
        """Unload model to free memory."""
        self.session = None
        logger.info("🧹 Rembg session unloaded")


# Convenience function
def remove_bg(image_path: str, output_path: str | None = None) -> str | None:
    """
    Quick function to remove background from an image.

    Args:
        image_path: Path to input image.
        output_path: Optional output path.

    Returns:
        Path to output image with transparent background.
    """
    remover = BackgroundRemover()
    return remover.remove_background(image_path, output_path)
