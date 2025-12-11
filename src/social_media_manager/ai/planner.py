import json
import logging
from typing import Any

from .brain import UnifiedBrain

logger = logging.getLogger(__name__)


class WorkflowPlanner:
    """
    The Architect.
    Now Context-Aware: Listens to user instructions before building the plan.

    Attributes:
        brain (UnifiedBrain): The AI brain instance for generating plans.
    """

    def __init__(self) -> None:
        """Initializes the WorkflowPlanner with a UnifiedBrain instance."""
        self.brain: UnifiedBrain = UnifiedBrain()

    def create_plan(
        self, video_info: dict, client_context: str, user_context: str = ""
    ) -> dict[str, Any]:
        """
        Creates a video processing plan based on video info and context.

        Args:
            video_info (Dict): Dictionary containing video metadata (filename, duration).
            client_context (str): The client's strategy or requirements.
            user_context (str, optional): Specific instructions from the user. Defaults to "".

        Returns:
            dict[str, Any]: A dictionary containing the execution plan (reasoning, workflow).
        """
        logger.info("🧠 Planner: Analyzing video strategy...")

        prompt = f"""
        Act as a Senior Post-Production Supervisor.

        INPUT DATA:
        - File Name: "{video_info.get("filename")}"
        - Duration: {video_info.get("duration")} seconds
        - Client Strategy: "{client_context}"
        - USER INSTRUCTIONS: "{user_context}" (CRITICAL)

        AVAILABLE TOOLS:
        1. smart_cut (Removes silence. WARNING: SKIP if user mentions 'music', 'cinematic', or 'short').
        2. transcribe (Generates subtitles. Use if there is speech).
        3. generate_caption (Writes the social post. ALWAYS required).
        4. generate_thumbnail (Creates AI art. Use if video is long > 60s).
        5. upload (Publishes video. ALWAYS required).

        TASK:
        Create a JSON execution plan.

        RULES:
        - If USER INSTRUCTIONS say "don't cut" or "music", DO NOT use 'smart_cut'.
        - If video is < 15s, keep it simple (caption + upload).

        OUTPUT JSON EXAMPLE:
        {{
            "reasoning": "User specified music video, so I am skipping smart_cut to preserve audio.",
            "workflow": ["generate_caption", "upload"]
        }}
        """

        try:
            # Use smart mode for better reasoning
            response = self.brain.think(prompt, mode="smart", json_mode=True)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Planning Error: {e}")
            return {
                "workflow": ["smart_cut", "transcribe", "generate_caption", "upload"]
            }
