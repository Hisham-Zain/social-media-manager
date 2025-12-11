from unittest.mock import patch

from social_media_manager.core.processor import VideoProcessor


def test_get_info_success(sample_video):
    """Test get_info returns correct metadata."""
    processor = VideoProcessor()

    # Mock VideoFileClip to avoid actual file processing
    with patch("social_media_manager.core.processor.VideoFileClip") as MockClip:
        mock_clip_instance = MockClip.return_value
        mock_clip_instance.duration = 10.5

        info = processor.get_info(sample_video)

        assert info is not None
        assert info["duration"] == 10.5
        assert info["filename"] == "test_video.mp4"
        mock_clip_instance.close.assert_called_once()


def test_get_info_failure():
    """Test get_info handles errors gracefully."""
    processor = VideoProcessor()

    with patch(
        "social_media_manager.core.processor.VideoFileClip",
        side_effect=Exception("Corrupt file"),
    ):
        info = processor.get_info("bad_path.mp4")

        assert info is not None
        assert info["duration"] == 0
        assert info["filename"] == "bad_path.mp4"


def test_create_static_video_success(tmp_path):
    """Test create_static_video logic."""
    processor = VideoProcessor()
    image_path = tmp_path / "image.jpg"
    audio_path = tmp_path / "audio.mp3"

    with (
        patch("social_media_manager.core.processor.ImageClip") as MockImage,
        patch("social_media_manager.core.processor.AudioFileClip") as MockAudio,
    ):
        mock_audio_instance = MockAudio.return_value
        mock_audio_instance.duration = 5.0

        mock_image_instance = MockImage.return_value
        mock_image_instance.set_duration.return_value = mock_image_instance
        mock_image_instance.set_audio.return_value = mock_image_instance

        output = processor.create_static_video(image_path, audio_path)

        assert output is not None
        assert output.endswith(".mp4")
        mock_image_instance.write_videofile.assert_called_once()
