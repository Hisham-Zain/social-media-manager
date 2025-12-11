import logging

import requests

from ..config import Config

logger = logging.getLogger(__name__)


class OllamaAI:
    """
    Interface for interacting with the Ollama API for text generation.

    Attributes:
        config (Config): The configuration instance.
        base_url (str): The base URL for the Ollama API.
        model (str): The Ollama model to use.
        api_url (str): The full API endpoint for generation.
    """

    def __init__(self) -> None:
        """
        Initialize the OllamaAI client.

        Loads configuration for the Ollama URL and model.
        """
        self.config: Config = Config()
        self.base_url: str = self.config.get("ollama_url") or "http://localhost:11434"
        self.model: str = self.config.get("ollama_model") or "llama3.2:3b"
        self.api_url: str = f"{self.base_url}/api/generate"

    def generate_caption(self, description: str, style: str = "engaging") -> str:
        """
        Generate a social media caption for a video.

        Args:
            description: Description of the video content.
            style: The desired style of the caption. Defaults to 'engaging'.

        Returns:
            The generated caption, or the original description if generation fails.
        """
        system = self.config.get("brand_voice", "You are a social media expert.")
        prompt = (
            f"Write a {style} caption for video: {description}. Include 3-5 hashtags."
        )
        try:
            resp = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            else:
                logger.warning(f"Ollama API returned {resp.status_code}")
                return description
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return description
