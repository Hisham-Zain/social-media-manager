from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from social_media_manager.cli import app

runner = CliRunner()


def test_cli_help():
    """Test that the CLI help command runs successfully."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Social Media Manager" in result.stdout


def test_cli_stats_success(mock_config):
    """Test the stats command."""
    # Mock the database call inside the manager
    with patch(
        "social_media_manager.core.orchestrator.SocialMediaManager"
    ) as MockManager:
        mock_instance = MockManager.return_value
        # Mock db.get_analytics returning a DataFrame-like object or just pass
        # The CLI calls manager.db.get_analytics()

        # We need to mock the pandas DataFrame returned by get_analytics
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__getitem__.return_value.sum.return_value = 100  # Mock sum
        mock_df.__len__.return_value = 5

        mock_instance.db.get_analytics.return_value = mock_df

        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Total Views" in result.stdout


def test_cli_upload_simulated(mock_config, sample_video):
    """Test the upload command with mocked processing."""
    with patch(
        "social_media_manager.core.orchestrator.SocialMediaManager"
    ) as MockManager:
        mock_instance = MockManager.return_value
        mock_instance.process_video.return_value = {
            "path": "processed.mp4",
            "caption": "Test Caption",
            "monetization": "Safe",
        }

        result = runner.invoke(
            app, ["upload", str(sample_video), "--platform", "youtube"]
        )
        assert result.exit_code == 0
        assert "Processing" in result.stdout
        assert "Success" in result.stdout
