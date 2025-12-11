"""
Image Upscaling and Face Restoration Module for AgencyOS.

Uses Real-ESRGAN for upscaling and GFPGAN for face restoration.
Optimized for RTX 2060 (6GB VRAM).
"""

import time
from pathlib import Path
from typing import Literal

from loguru import logger

from ..config import config

# Lazy imports for heavy dependencies
REALESRGAN_AVAILABLE = False
GFPGAN_AVAILABLE = False


class ImageUpscaler:
    """
    AI Image Upscaling using Real-ESRGAN.

    Supports multiple models:
    - RealESRGAN_x4plus: General images (4x)
    - RealESRGAN_x2plus: General images (2x)
    - RealESRNet_x4plus: Fast/lightweight (4x)
    - realesr-animevideov3: Anime/illustration
    """

    MODELS = {
        "x4plus": "RealESRGAN_x4plus",
        "x2plus": "RealESRGAN_x2plus",
        "x4fast": "RealESRNet_x4plus",
        "anime": "realesr-animevideov3",
    }

    def __init__(
        self,
        model: Literal["x4plus", "x2plus", "x4fast", "anime"] = "x4plus",
        gpu_id: int = 0,
    ) -> None:
        """
        Initialize ImageUpscaler.

        Args:
            model: Model to use for upscaling.
            gpu_id: GPU device ID (-1 for CPU).
        """
        self.model_name = self.MODELS.get(model, "RealESRGAN_x4plus")
        self.gpu_id = gpu_id
        self.upsampler = None
        self.output_dir = Path(config.PROCESSED_DIR) / "upscaled"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_model(self) -> bool:
        """Load the Real-ESRGAN model."""
        if self.upsampler is not None:
            return True

        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer

            # Model configurations
            if "x4plus" in self.model_name:
                model = RRDBNet(
                    num_in_ch=3,
                    num_out_ch=3,
                    num_feat=64,
                    num_block=23,
                    num_grow_ch=32,
                    scale=4,
                )
                netscale = 4
            elif "x2plus" in self.model_name:
                model = RRDBNet(
                    num_in_ch=3,
                    num_out_ch=3,
                    num_feat=64,
                    num_block=23,
                    num_grow_ch=32,
                    scale=2,
                )
                netscale = 2
            else:
                model = RRDBNet(
                    num_in_ch=3,
                    num_out_ch=3,
                    num_feat=64,
                    num_block=23,
                    num_grow_ch=32,
                    scale=4,
                )
                netscale = 4

            self.upsampler = RealESRGANer(
                scale=netscale,
                model_path=None,  # Auto-download
                model=model,
                tile=400,  # Tile size for memory efficiency
                tile_pad=10,
                pre_pad=0,
                half=True,  # FP16 for RTX 2060
                gpu_id=self.gpu_id,
            )

            logger.info(f"✅ Real-ESRGAN loaded: {self.model_name}")
            return True

        except ImportError:
            logger.error("❌ Real-ESRGAN not installed. Run: pip install realesrgan")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load Real-ESRGAN: {e}")
            return False

    def upscale(
        self,
        image_path: str,
        output_path: str | None = None,
        outscale: float = 4.0,
    ) -> str | None:
        """
        Upscale an image.

        Args:
            image_path: Path to input image.
            output_path: Optional output path.
            outscale: Output scale factor (default 4x).

        Returns:
            Path to upscaled image.
        """
        if not self._load_model():
            return None

        try:
            import cv2

            input_path = Path(image_path)
            logger.info(f"🔍 Upscaling: {input_path.name} ({outscale}x)")
            start_time = time.time()

            # Read image
            img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
            if img is None:
                logger.error(f"❌ Could not read image: {image_path}")
                return None

            # Upscale
            output, _ = self.upsampler.enhance(img, outscale=outscale)

            # Determine output path
            if output_path is None:
                output_path = self.output_dir / f"{input_path.stem}_upscaled.png"

            # Save
            cv2.imwrite(str(output_path), output)

            elapsed = time.time() - start_time
            logger.info(f"✅ Upscaled in {elapsed:.1f}s → {Path(output_path).name}")

            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Upscaling failed: {e}")
            return None

    def upscale_with_face_enhance(
        self,
        image_path: str,
        output_path: str | None = None,
    ) -> str | None:
        """
        Upscale image and enhance faces with GFPGAN.

        Args:
            image_path: Path to input image.
            output_path: Optional output path.

        Returns:
            Path to upscaled and face-enhanced image.
        """
        try:
            from gfpgan import GFPGANer

            if not self._load_model():
                return None

            # Initialize face enhancer
            face_enhancer = GFPGANer(
                model_path=None,  # Auto-download
                upscale=4,
                arch="clean",
                channel_multiplier=2,
                bg_upsampler=self.upsampler,
            )

            import cv2

            input_path = Path(image_path)
            logger.info(f"🔍 Upscaling + Face Enhancement: {input_path.name}")
            start_time = time.time()

            img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)

            # Enhance faces
            _, _, output = face_enhancer.enhance(
                img,
                has_aligned=False,
                only_center_face=False,
                paste_back=True,
            )

            # Determine output path
            if output_path is None:
                output_path = self.output_dir / f"{input_path.stem}_enhanced.png"

            cv2.imwrite(str(output_path), output)

            elapsed = time.time() - start_time
            logger.info(f"✅ Enhanced in {elapsed:.1f}s → {Path(output_path).name}")

            return str(output_path)

        except ImportError:
            logger.error("❌ GFPGAN not installed. Run: pip install gfpgan")
            return None
        except Exception as e:
            logger.error(f"❌ Face enhancement failed: {e}")
            return None


class FaceRestorer:
    """
    Face Restoration using GFPGAN.

    Restores and enhances faces in images - perfect for:
    - Old/damaged photos
    - Low quality images
    - AI-generated faces
    """

    def __init__(self, gpu_id: int = 0) -> None:
        """Initialize FaceRestorer."""
        self.gpu_id = gpu_id
        self.face_enhancer = None
        self.output_dir = Path(config.PROCESSED_DIR) / "restored"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_model(self) -> bool:
        """Load GFPGAN model."""
        if self.face_enhancer is not None:
            return True

        try:
            from gfpgan import GFPGANer

            self.face_enhancer = GFPGANer(
                model_path=None,  # Auto-download GFPGANv1.4
                upscale=2,
                arch="clean",
                channel_multiplier=2,
                bg_upsampler=None,  # No background upscaling
            )

            logger.info("✅ GFPGAN loaded")
            return True

        except ImportError:
            logger.error("❌ GFPGAN not installed. Run: pip install gfpgan")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load GFPGAN: {e}")
            return False

    def restore(
        self,
        image_path: str,
        output_path: str | None = None,
        only_center_face: bool = False,
    ) -> str | None:
        """
        Restore faces in an image.

        Args:
            image_path: Path to input image.
            output_path: Optional output path.
            only_center_face: Only restore the center/main face.

        Returns:
            Path to restored image.
        """
        if not self._load_model():
            return None

        try:
            import cv2

            input_path = Path(image_path)
            logger.info(f"👤 Restoring faces: {input_path.name}")
            start_time = time.time()

            img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
            if img is None:
                logger.error(f"❌ Could not read image: {image_path}")
                return None

            # Restore faces
            _, _, output = self.face_enhancer.enhance(
                img,
                has_aligned=False,
                only_center_face=only_center_face,
                paste_back=True,
            )

            # Determine output path
            if output_path is None:
                output_path = self.output_dir / f"{input_path.stem}_restored.png"

            cv2.imwrite(str(output_path), output)

            elapsed = time.time() - start_time
            logger.info(f"✅ Restored in {elapsed:.1f}s → {Path(output_path).name}")

            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Face restoration failed: {e}")
            return None

    def batch_restore(
        self,
        image_paths: list[str],
        output_dir: str | None = None,
    ) -> list[str]:
        """Restore faces in multiple images."""
        if not self._load_model():
            return []

        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for i, img_path in enumerate(image_paths):
            logger.info(f"👤 Processing {i + 1}/{len(image_paths)}")
            output = self.restore(
                img_path,
                output_path=str(out_dir / f"{Path(img_path).stem}_restored.png"),
            )
            if output:
                results.append(output)

        return results


# Convenience functions
def upscale_image(image_path: str, scale: float = 4.0) -> str | None:
    """Quick upscale an image."""
    upscaler = ImageUpscaler()
    return upscaler.upscale(image_path, outscale=scale)


def restore_faces(image_path: str) -> str | None:
    """Quick restore faces in an image."""
    restorer = FaceRestorer()
    return restorer.restore(image_path)


def enhance_image(image_path: str) -> str | None:
    """Upscale + face restoration in one step."""
    upscaler = ImageUpscaler()
    return upscaler.upscale_with_face_enhance(image_path)
