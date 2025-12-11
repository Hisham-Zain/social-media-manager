import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src to pythonpath
sys.path.append(str(Path(__file__).parent.parent / "src"))

from social_media_manager.ai.brain import Brain


@pytest.fixture
def mock_config(monkeypatch):
    """Mock environment variables and config."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_groq_key")
    monkeypatch.setenv("GEMINI_API_KEY", "mock_gemini_key")
    monkeypatch.setenv("HF_TOKEN", "mock_hf_token")

    # Mock the config object directly if needed, but env vars usually suffice
    # for the Config class initialization if it reads os.getenv


@pytest.fixture
def mock_brain():
    """Mock the Brain class to avoid real API calls."""
    brain = MagicMock(spec=Brain)
    brain.mode = "mock"
    brain.think.return_value = "Mocked AI Response"
    return brain


@pytest.fixture
def sample_video(tmp_path):
    """Create a dummy video file."""
    video_path = tmp_path / "test_video.mp4"
    video_path.write_text("dummy video content")
    return video_path
