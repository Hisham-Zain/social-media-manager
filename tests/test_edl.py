"""
Unit tests for the Edit Decision List (EDL) system.

Tests the EDL class for non-destructive video editing.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from social_media_manager.core.edl import (
    ClipSegment,
    EditDecisionList,
    create_edl_from_assets,
)


class TestClipSegment:
    """Tests for the ClipSegment dataclass."""

    def test_segment_creation(self) -> None:
        """Test creating a segment with defaults."""
        seg = ClipSegment(asset_path="/path/to/video.mp4")
        assert seg.asset_path == "/path/to/video.mp4"
        assert seg.start_time == 0.0
        assert seg.end_time == 3.0
        assert seg.transition_in == "cut"

    def test_segment_duration(self) -> None:
        """Test duration calculation."""
        seg = ClipSegment(start_time=5.0, end_time=10.0)
        assert seg.duration == 5.0

    def test_segment_serialization(self) -> None:
        """Test to_dict and from_dict."""
        seg = ClipSegment(
            asset_path="/path.mp4",
            start_time=1.0,
            end_time=5.0,
            filters=["grayscale"],
            volume=0.8,
        )
        data = seg.to_dict()

        restored = ClipSegment.from_dict(data)
        assert restored.asset_path == seg.asset_path
        assert restored.start_time == seg.start_time
        assert restored.filters == seg.filters
        assert restored.volume == seg.volume


class TestEditDecisionList:
    """Tests for the EditDecisionList class."""

    def test_edl_creation(self) -> None:
        """Test creating an EDL."""
        edl = EditDecisionList("Test Project")
        assert edl.project_name == "Test Project"
        assert edl.segments == []
        assert edl.fps == 30

    def test_add_segment(self) -> None:
        """Test adding segments."""
        edl = EditDecisionList()
        seg = ClipSegment(asset_path="/video1.mp4")
        idx = edl.add_segment(seg)

        assert idx == 0
        assert len(edl.segments) == 1
        assert edl.segment_count == 1

    def test_get_segment(self) -> None:
        """Test retrieving segments."""
        edl = EditDecisionList()
        edl.add_segment(ClipSegment(asset_path="/video1.mp4"))

        seg = edl.get_segment(0)
        assert seg is not None
        assert seg.asset_path == "/video1.mp4"

        # Invalid index
        assert edl.get_segment(99) is None

    def test_update_segment(self) -> None:
        """Test updating segment properties."""
        edl = EditDecisionList()
        edl.add_segment(ClipSegment(asset_path="/video.mp4", end_time=5.0))

        updated = edl.update_segment(0, end_time=10.0, volume=0.5)
        assert updated is not None
        assert updated.end_time == 10.0
        assert updated.volume == 0.5

    def test_swap_segment(self) -> None:
        """Test swapping segment assets."""
        edl = EditDecisionList()
        edl.add_segment(ClipSegment(asset_path="/old.mp4", end_time=5.0))

        updated = edl.swap_segment(0, "/new.mp4")
        assert updated is not None
        assert updated.asset_path == "/new.mp4"
        assert updated.end_time == 5.0  # Preserved

    def test_remove_segment(self) -> None:
        """Test removing segments."""
        edl = EditDecisionList()
        edl.add_segment(ClipSegment(asset_path="/video1.mp4"))
        edl.add_segment(ClipSegment(asset_path="/video2.mp4"))

        assert edl.remove_segment(0) is True
        assert len(edl.segments) == 1
        assert edl.segments[0].asset_path == "/video2.mp4"

    def test_reorder_segment(self) -> None:
        """Test reordering segments."""
        edl = EditDecisionList()
        edl.add_segment(ClipSegment(asset_path="/first.mp4"))
        edl.add_segment(ClipSegment(asset_path="/second.mp4"))

        assert edl.reorder_segment(1, 0) is True
        assert edl.segments[0].asset_path == "/second.mp4"

    def test_total_duration(self) -> None:
        """Test total duration calculation."""
        edl = EditDecisionList()
        edl.add_segment(ClipSegment(end_time=5.0))
        edl.add_segment(ClipSegment(end_time=10.0))

        assert edl.total_duration == 15.0

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        edl = EditDecisionList("JSON Test")
        edl.add_segment(ClipSegment(asset_path="/test.mp4", end_time=5.0))

        json_str = edl.to_json()
        restored = EditDecisionList.from_json(json_str)

        assert restored.project_name == "JSON Test"
        assert len(restored.segments) == 1
        assert restored.segments[0].end_time == 5.0

    def test_save_and_load(self) -> None:
        """Test file save/load."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_edl.json"

            edl = EditDecisionList("Save Test")
            edl.add_segment(ClipSegment(asset_path="/video.mp4"))
            edl.save(path)

            loaded = EditDecisionList.load(path)
            assert loaded.project_name == "Save Test"
            assert len(loaded.segments) == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_edl_from_assets(self) -> None:
        """Test quick EDL creation."""
        assets = ["/video1.mp4", "/video2.mp4", "/video3.mp4"]
        edl = create_edl_from_assets(assets, project_name="Quick Project")

        assert edl.project_name == "Quick Project"
        assert len(edl.segments) == 3
        assert edl.segments[0].asset_path == "/video1.mp4"
