import logging
import time
from pathlib import Path

import requests

from ..config import config
from .brain import HybridBrain

logger = logging.getLogger(__name__)

# --- FIX: MoviePy v2 Import ---
try:
    from moviepy import ImageClip

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("⚠️ MoviePy not found. Video rendering disabled.")


class VideoDirector:
    """
    Agent responsible for AI Image and Video generation.

    Supports style consistency through StyleConfig injection,
    ensuring all generated images maintain a cohesive aesthetic.
    """

    def __init__(
        self,
        brain: HybridBrain | None = None,
        style_config: "StyleConfig | None" = None,
    ) -> None:
        self.brain = brain if brain else HybridBrain()
        self.hf_token = config.HF_TOKEN
        self.output_dir = config.PROCESSED_DIR
        self.thumb_dir = config.THUMB_DIR
        self.thumb_dir.mkdir(parents=True, exist_ok=True)

        # Style consistency
        self._style_config = style_config
        self._global_style_prompt: str = ""
        self._style_seed: int | None = None

    def set_style(
        self,
        style_prompt: str | None = None,
        seed: int | None = None,
        config: "StyleConfig | None" = None,
    ) -> None:
        """
        Set the global style for all subsequent generations.

        Args:
            style_prompt: Style string to append to all prompts.
            seed: Fixed seed for character consistency.
            config: Full StyleConfig object (overrides other params).
        """
        if config:
            self._style_config = config
            self._global_style_prompt = config.style_prompt
            self._style_seed = config.seed
            logger.info(f"🎨 Style set: preset={config.preset}, seed={config.seed}")
        else:
            self._global_style_prompt = style_prompt or ""
            self._style_seed = seed
            logger.info(
                f"🎨 Style set: '{style_prompt[:30] if style_prompt else 'none'}...'"
            )

    @property
    def style_config(self) -> "StyleConfig | None":
        """Get current style configuration."""
        return self._style_config

    def _apply_style(self, prompt: str) -> str:
        """Apply style to a prompt."""
        if self._style_config:
            return self._style_config.get_full_prompt(prompt)
        elif self._global_style_prompt:
            return f"{prompt}, {self._global_style_prompt}"
        return prompt

    def generate_image(
        self, prompt: str, output_folder: Path | None = None
    ) -> str | None:
        if not self.hf_token:
            logger.warning("⚠️ Director: Missing HF_TOKEN. Cannot generate images.")
            return None

        folder = output_folder if output_folder else self.output_dir
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {self.hf_token}"}

        # Apply global style to prompt
        styled_prompt = self._apply_style(prompt)
        logger.info(f"🎨 Director: Generating image for '{styled_prompt[:50]}...'")

        # Build payload with optional seed
        payload: dict[str, str | int] = {"inputs": styled_prompt}
        if self._style_seed is not None:
            payload["seed"] = self._style_seed

        try:
            res = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            res.raise_for_status()

            path = folder / f"img_{int(time.time())}.jpg"
            with open(path, "wb") as f:
                f.write(res.content)

            return str(path)
        except Exception as e:
            logger.error(f"❌ Image Generation Failed: {e}")
            return None

    def create_thumbnail(self, topic: str) -> str | None:
        """Generates a high-CTR thumbnail for a topic."""
        try:
            concept = self.brain.think(
                f"Describe a YouTube thumbnail for '{topic}'. Visual description only."
            )
            return self.generate_image(concept, output_folder=self.thumb_dir)
        except Exception as e:
            logger.error(f"❌ Thumbnail Failed: {e}")
            return None

    def generate_scene(self, topic: str) -> str | None:
        """Creates a simple static video scene from an AI image."""
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ Cannot generate scene: MoviePy is not available.")
            return None

        try:
            import json

            plan_json = self.brain.think(
                f"Topic: {topic}. JSON with 'script_text' and 'image_prompt'.",
                json_mode=True,
            )
            data = json.loads(plan_json)

            img_path = self.generate_image(data.get("image_prompt", topic))
            if not img_path:
                return None

            # --- FIX: MoviePy v2 Syntax ---
            # v2 uses .with_duration() instead of .set_duration()
            # v2 uses .resized() instead of .resize()
            clip = ImageClip(img_path).with_duration(5).resized(height=1080)

            path = self.output_dir / f"gen_{int(time.time())}.mp4"
            clip.write_videofile(str(path), fps=24, codec="libx264", logger=None)

            return str(path)

        except Exception as e:
            logger.error(f"❌ Scene Generation Failed: {e}")
            return None

    # --- Storyboard Methods (Pre-Visualization) ---

    def generate_storyboard(
        self,
        script: str,
        project_name: str = "Untitled",
        target_duration: int = 60,
        generate_previews: bool = True,
    ) -> "Storyboard":
        """
        Break a script into visual scenes for pre-visualization.

        Args:
            script: Full script/narration text.
            project_name: Name for the storyboard project.
            target_duration: Target total duration in seconds.
            generate_previews: If True, generate preview images immediately.

        Returns:
            Storyboard object with scenes ready for review.
        """
        import json
        import uuid
        from datetime import datetime

        from ..models import Scene, Storyboard

        logger.info(f"📋 Generating storyboard for '{project_name}'...")

        # Step 1: Use AI to break script into scenes
        prompt = f"""Break this script into 5-10 visual scenes for a video.

Script:
{script}

Target duration: {target_duration} seconds total.

Return JSON array with objects containing:
- "script_segment": The narration text for this scene (from the script)
- "visual_prompt": Detailed image generation prompt (cinematic, professional style)
- "duration": Scene duration in seconds (3-10s each)

Example:
[
  {{"script_segment": "Welcome to our channel...", "visual_prompt": "Professional presenter in modern studio, warm lighting, 4K", "duration": 5}},
  ...
]

Return ONLY the JSON array, no explanation."""

        try:
            result = self.brain.think(prompt, json_mode=True)
            scenes_data = json.loads(result)

            if not isinstance(scenes_data, list):
                scenes_data = [scenes_data]

        except Exception as e:
            logger.error(f"❌ Failed to parse scene breakdown: {e}")
            # Fallback: single scene with full script
            scenes_data = [
                {
                    "script_segment": script,
                    "visual_prompt": f"Cinematic visual for: {script[:100]}",
                    "duration": min(target_duration, 30),
                }
            ]

        # Step 2: Create Scene objects
        scenes: list[Scene] = []
        for i, scene_data in enumerate(scenes_data):
            scene = Scene(
                id=i,
                script_segment=scene_data.get("script_segment", ""),
                visual_prompt=scene_data.get("visual_prompt", ""),
                duration=min(max(scene_data.get("duration", 5), 0.5), 30),
                status="pending",
            )
            scenes.append(scene)

        # Step 3: Create Storyboard
        storyboard = Storyboard(
            id=str(uuid.uuid4())[:8],
            project_name=project_name,
            scenes=scenes,
            status="generating" if generate_previews else "draft",
            created_at=datetime.now().isoformat(),
        )
        storyboard.calculate_duration()

        logger.info(
            f"📋 Created {len(scenes)} scenes (total: {storyboard.total_duration:.1f}s)"
        )

        # Step 4: Generate preview images if requested
        if generate_previews:
            for scene in storyboard.scenes:
                self._generate_scene_preview(scene)
            storyboard.status = "reviewing"

        return storyboard

    def _generate_scene_preview(self, scene: "Scene") -> bool:
        """Generate a preview image for a single scene."""

        scene.status = "generating"
        try:
            img_path = self.generate_image(scene.visual_prompt)
            if img_path:
                scene.image_path = img_path
                scene.status = "generated"
                logger.info(f"✅ Scene {scene.id}: Preview generated")
                return True
            else:
                scene.status = "failed"
                scene.error = "Image generation returned None"
                return False
        except Exception as e:
            scene.status = "failed"
            scene.error = str(e)
            logger.error(f"❌ Scene {scene.id}: Preview failed: {e}")
            return False

    def regenerate_scene(
        self, storyboard: "Storyboard", scene_id: int
    ) -> "Scene | None":
        """
        Regenerate the visual for a specific scene.

        Args:
            storyboard: The storyboard containing the scene.
            scene_id: Index of the scene to regenerate.

        Returns:
            Updated Scene object, or None if failed.
        """

        if scene_id < 0 or scene_id >= len(storyboard.scenes):
            logger.error(f"❌ Invalid scene_id: {scene_id}")
            return None

        scene = storyboard.scenes[scene_id]
        scene.image_path = None  # Clear old image
        scene.stock_path = None  # Clear stock if any

        logger.info(f"🔄 Regenerating scene {scene_id}...")
        self._generate_scene_preview(scene)

        return scene

    def swap_with_stock(
        self,
        scene: "Scene",
        stock_query: str | None = None,
    ) -> "Scene":
        """
        Replace a scene's AI image with stock footage.

        Args:
            scene: The scene to modify.
            stock_query: Search query for stock footage. If None, uses visual_prompt.

        Returns:
            Updated Scene with stock_path set.
        """

        try:
            from .hunter import StockHunter

            hunter = StockHunter()
            query = stock_query or scene.visual_prompt[:50]

            logger.info(
                f"🔍 Searching stock footage for scene {scene.id}: '{query[:30]}...'"
            )

            # Try video first, fall back to image
            results = hunter.search_videos(query, limit=1)
            if results:
                scene.stock_path = results[0].get("video_path") or results[0].get("url")
                logger.info(f"✅ Scene {scene.id}: Found stock video")
            else:
                # Try image
                image_results = hunter.search_images(query, limit=1)
                if image_results:
                    scene.stock_path = image_results[0].get("path") or image_results[
                        0
                    ].get("url")
                    logger.info(f"✅ Scene {scene.id}: Found stock image")

            if scene.stock_path:
                scene.status = "generated"
            else:
                logger.warning(f"⚠️ Scene {scene.id}: No stock footage found")

        except ImportError:
            logger.warning("⚠️ StockHunter not available for stock swap")
        except Exception as e:
            logger.error(f"❌ Stock swap failed: {e}")

        return scene

    # === MCP-BASED METHODS ===

    async def generate_video_with_mcp(
        self,
        images: list[str],
        output_path: str | None = None,
        fps: int = 24,
        transition: str = "fade",
    ) -> str | None:
        """
        Generate video from images using FFmpeg MCP.

        Allows the LLM to orchestrate complex FFmpeg operations
        for video creation without hardcoding filter graphs.

        Args:
            images: List of image paths
            output_path: Output video path
            fps: Frames per second
            transition: Transition type (fade, dissolve, wipe)

        Returns:
            Path to generated video, or None if failed
        """
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "ffmpeg" not in manager.servers:
                logger.debug("FFmpeg MCP not configured, using local MoviePy")
                return self._generate_video_local(images, output_path, fps)

            output = output_path or str(
                self.output_dir / f"video_{int(time.time())}.mp4"
            )

            logger.info(f"🎬 MCP Video: Creating from {len(images)} images...")

            result = await manager.call_tool(
                "ffmpeg",
                "create_slideshow",
                {
                    "images": images,
                    "output": output,
                    "fps": fps,
                    "transition": transition,
                },
            )

            if "error" in result:
                logger.warning(f"MCP video failed: {result['error']}")
                return self._generate_video_local(images, output_path, fps)

            return result.get("output_path", output)

        except ImportError:
            logger.debug("MCP client not available")
            return self._generate_video_local(images, output_path, fps)
        except Exception as e:
            logger.error(f"MCP video error: {e}")
            return self._generate_video_local(images, output_path, fps)

    def _generate_video_local(
        self,
        images: list[str],
        output_path: str | None,
        fps: int,
    ) -> str | None:
        """Fallback: Generate video locally with MoviePy."""
        if not MOVIEPY_AVAILABLE:
            logger.error("MoviePy not available for local video generation")
            return None

        try:
            from moviepy import concatenate_videoclips

            clips = []
            for img_path in images:
                clip = ImageClip(img_path).with_duration(3)
                clips.append(clip)

            final = concatenate_videoclips(clips, method="compose")
            output = output_path or str(
                self.output_dir / f"video_{int(time.time())}.mp4"
            )
            final.write_videofile(output, fps=fps, codec="libx264", logger=None)

            return output
        except Exception as e:
            logger.error(f"Local video generation failed: {e}")
            return None

    async def edit_video_with_mcp(
        self,
        video_path: str,
        edits: list[dict],
    ) -> str | None:
        """
        Apply edits to video using FFmpeg MCP.

        Args:
            video_path: Path to input video
            edits: List of edit operations, e.g.:
                [{"type": "trim", "start": 0, "end": 10},
                 {"type": "speed", "factor": 1.5}]

        Returns:
            Path to edited video
        """
        try:
            from ..core.mcp_client import get_mcp_manager, initialize_mcp

            manager = get_mcp_manager()
            if not manager._initialized:
                await initialize_mcp()

            if "ffmpeg" not in manager.servers:
                logger.warning("FFmpeg MCP not available for editing")
                return None

            output = str(self.output_dir / f"edited_{int(time.time())}.mp4")

            result = await manager.call_tool(
                "ffmpeg",
                "edit_video",
                {
                    "input": video_path,
                    "output": output,
                    "edits": edits,
                },
            )

            if "error" in result:
                logger.error(f"Video edit failed: {result['error']}")
                return None

            return result.get("output_path", output)

        except Exception as e:
            logger.error(f"MCP edit error: {e}")
            return None
