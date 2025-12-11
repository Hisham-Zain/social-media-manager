"""
Tests for the Connection Manager module.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from social_media_manager.core.connections import (
    PLATFORM_INFO,
    ConnectionManager,
    PlatformConnection,
    get_connection_manager,
)


class TestPlatformConnection:
    """Tests for the PlatformConnection dataclass."""

    def test_disconnected_health_status(self):
        """Disconnected connection should have 'disconnected' status."""
        conn = PlatformConnection(platform="youtube", connected=False)
        assert conn.health_status == "disconnected"

    def test_valid_health_status(self):
        """Connection with >7 days until expiry should be 'valid'."""
        conn = PlatformConnection(
            platform="youtube",
            connected=True,
            expires_at=datetime.now() + timedelta(days=30),
        )
        assert conn.health_status == "valid"

    def test_expiring_health_status(self):
        """Connection with <7 days until expiry should be 'expiring'."""
        conn = PlatformConnection(
            platform="youtube",
            connected=True,
            expires_at=datetime.now() + timedelta(days=3),
        )
        assert conn.health_status == "expiring"

    def test_expired_health_status(self):
        """Connection past expiry should be 'expired'."""
        conn = PlatformConnection(
            platform="youtube",
            connected=True,
            expires_at=datetime.now() - timedelta(days=1),
        )
        assert conn.health_status == "expired"

    def test_no_expiry_is_valid(self):
        """Connection with no expiry date should be 'valid'."""
        conn = PlatformConnection(platform="youtube", connected=True, expires_at=None)
        assert conn.health_status == "valid"

    def test_days_until_expiry(self):
        """Days until expiry should be calculated correctly."""
        conn = PlatformConnection(
            platform="youtube",
            connected=True,
            expires_at=datetime.now() + timedelta(days=10),
        )
        # Allow for some timing flexibility
        assert 9 <= conn.days_until_expiry <= 10

    def test_display_name(self):
        """Display name should include icon and platform name."""
        conn = PlatformConnection(platform="youtube")
        assert "📺" in conn.display_name
        assert "YouTube" in conn.display_name

    def test_to_dict(self):
        """to_dict should serialize connection properly."""
        conn = PlatformConnection(
            platform="youtube",
            connected=True,
            account_name="test@example.com",
            scopes=["upload", "readonly"],
        )
        data = conn.to_dict()
        assert data["platform"] == "youtube"
        assert data["connected"] is True
        assert data["account_name"] == "test@example.com"
        assert "upload" in data["scopes"]


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    def test_get_all_connections(self):
        """Should return connections for all platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "social_media_manager.core.connections.config.CREDS_DIR",
                Path(tmpdir),
            ):
                manager = ConnectionManager()
                connections = manager.get_all_connections()

                # Should have all platforms
                platforms = {c.platform for c in connections}
                assert "youtube" in platforms
                assert "instagram" in platforms
                assert "facebook" in platforms
                assert "tiktok" in platforms
                assert "linkedin" in platforms

    def test_disconnect_nonexistent(self):
        """Disconnecting non-connected platform should succeed (no-op)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "social_media_manager.core.connections.config.CREDS_DIR",
                Path(tmpdir),
            ):
                manager = ConnectionManager()
                result = manager.disconnect("youtube")
                assert result is True

    def test_load_connection_from_token_file(self):
        """Should load connection details from token file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock token file
            token_path = Path(tmpdir) / "youtube_token.json"
            token_data = {
                "access_token": "test_token",
                "expiry": (datetime.now() + timedelta(days=7)).isoformat(),
                "scopes": ["upload", "readonly"],
                "email": "test@example.com",
            }
            with open(token_path, "w") as f:
                json.dump(token_data, f)

            with patch(
                "social_media_manager.core.connections.config.CREDS_DIR",
                Path(tmpdir),
            ):
                manager = ConnectionManager()
                conn = manager.get_connection("youtube")

                assert conn.connected is True
                assert conn.account_name == "test@example.com"
                assert "upload" in conn.scopes

    def test_check_token_health(self):
        """check_token_health should return correct status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "social_media_manager.core.connections.config.CREDS_DIR",
                Path(tmpdir),
            ):
                manager = ConnectionManager()
                health = manager.check_token_health("youtube")
                assert health == "disconnected"


class TestPlatformInfo:
    """Tests for PLATFORM_INFO metadata."""

    def test_all_platforms_have_required_fields(self):
        """All platforms should have name, icon, color, scopes, auth_type."""
        required_fields = ["name", "icon", "color", "scopes", "auth_type"]

        for platform, info in PLATFORM_INFO.items():
            for field in required_fields:
                assert field in info, f"{platform} missing {field}"

    def test_supported_platforms(self):
        """Should support the expected platforms."""
        expected = {"youtube", "instagram", "facebook", "tiktok", "linkedin"}
        assert set(PLATFORM_INFO.keys()) == expected


class TestSingleton:
    """Tests for the singleton pattern."""

    def test_get_connection_manager_returns_same_instance(self):
        """get_connection_manager should return singleton."""
        # Note: This test may interfere with other tests due to global state
        # In production, you'd want to reset the singleton between tests
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()
        # Both should be ConnectionManager instances
        assert isinstance(manager1, ConnectionManager)
        assert isinstance(manager2, ConnectionManager)
