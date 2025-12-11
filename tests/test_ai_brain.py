from unittest.mock import patch

from social_media_manager.ai.brain import Brain


def test_brain_initialization_groq(mock_config):
    """Test Brain initializes with Groq when key is present."""
    with patch("social_media_manager.ai.brain.Groq") as MockGroq:
        brain = Brain()
        assert brain.mode == "groq"
        MockGroq.assert_called_once()


def test_brain_think_groq_success(mock_config):
    """Test think method using Groq."""
    with patch("social_media_manager.ai.brain.Groq") as MockGroq:
        brain = Brain()
        brain.groq_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Groq Response"

        response = brain.think("Hello")
        assert response == "Groq Response"


def test_brain_fallback_to_ollama(mock_config):
    """Test fallback to Ollama when primary fails."""
    with (
        patch("social_media_manager.ai.brain.Groq", side_effect=ImportError),
        patch("social_media_manager.ai.brain.requests.post") as mock_post,
        patch("social_media_manager.ai.brain.requests.get") as mock_get,
    ):
        # Mock Ollama check
        mock_get.return_value.status_code = 200

        # Mock Ollama generation
        mock_post.return_value.json.return_value = {"response": "Ollama Response"}
        mock_post.return_value.status_code = 200

        brain = Brain()
        # Force mode to offline to trigger fallback check logic in think() if we didn't mock init completely
        # But here init should fail Groq and Gemini (missing key in this specific test setup if we wanted)
        # Actually mock_config sets keys, so we need to simulate init failure.

        # Let's manually set up the state for fallback testing
        brain.mode = "offline"
        brain.ollama_ready = True

        response = brain.think("Hello")
        assert response == "Ollama Response"
        assert brain.mode == "ollama"
