import logging
from pathlib import Path

from PIL import Image, UnidentifiedImageError

try:
    from sentence_transformers import SentenceTransformer, util

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from ..config import config

logger = logging.getLogger(__name__)


class SmartCurator:
    """
    Local Computer Vision agent. Finds the best image for a caption using CLIP.
    """

    def __init__(self, asset_folder: Path | None = None):
        self.asset_folder = asset_folder if asset_folder else config.ASSETS_DIR
        self.asset_folder.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.embeddings = []
        self.image_paths = []

        if TRANSFORMERS_AVAILABLE:
            try:
                # Load CLIP model (optimized for speed/accuracy)
                self.model = SentenceTransformer("clip-ViT-B-32")
                self._index_images()
            except Exception as e:
                logger.error(f"❌ Curator Init Failed: {e}")
        else:
            logger.warning("⚠️ sentence-transformers not installed. Curator disabled.")

    def _index_images(self) -> None:
        """Pre-scan all images in the folder and compute their embeddings."""
        if not self.model:
            return

        logger.info(f"👁️ Curator: Scanning assets in {self.asset_folder}...")
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}

        # Clear existing cache
        self.embeddings = []
        self.image_paths = []

        for file in self.asset_folder.glob("*"):
            if file.suffix.lower() in valid_extensions:
                try:
                    img = Image.open(file)
                    # Generate embedding
                    emb = self.model.encode(img)
                    self.embeddings.append(emb)
                    self.image_paths.append(str(file))
                except UnidentifiedImageError:
                    logger.warning(f"⚠️ Corrupt image skipped: {file.name}")
                except Exception as e:
                    logger.warning(f"⚠️ Error indexing {file.name}: {e}")

        logger.info(f"👁️ Indexed {len(self.image_paths)} images.")

    def find_best_match(self, text_query: str) -> str | None:
        """Find the image that best matches the text description."""
        if not self.model or not self.embeddings:
            return None

        try:
            # Encode text
            text_emb = self.model.encode(text_query)

            # Calculate similarity
            scores = util.cos_sim(text_emb, self.embeddings)[0]

            # Find best match
            best_idx = scores.argmax()
            best_score = scores[best_idx]

            if best_score < 0.2:  # Threshold for relevance
                logger.info(
                    f"search '{text_query}' had low relevance ({best_score:.2f})"
                )
                return None

            best_path = self.image_paths[best_idx]
            logger.info(
                f"🎯 Curator Match: {Path(best_path).name} (Score: {best_score:.2f})"
            )
            return best_path

        except Exception as e:
            logger.error(f"❌ Curator Search Error: {e}")
            return None
