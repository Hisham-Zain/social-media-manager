"""
Unit tests for the Autonomy Engine.

Tests the AutonomyEngine class including goals, state machine,
and the daily cycle.
"""

from unittest.mock import MagicMock, patch

import pytest

from social_media_manager.core.autonomy import (
    AutonomyEngine,
    AutonomyState,
    Goal,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock DatabaseManager."""
    db = MagicMock()
    db.get_analytics.return_value = None
    return db


@pytest.fixture
def mock_brain() -> MagicMock:
    """Create a mock HybridBrain."""
    brain = MagicMock()
    brain.think.return_value = "Generated content"
    return brain


@pytest.fixture
def engine(mock_db: MagicMock, mock_brain: MagicMock) -> AutonomyEngine:
    """Create an AutonomyEngine instance with mocked dependencies."""
    return AutonomyEngine(db=mock_db, brain=mock_brain, client_niche="Tech")


class TestGoal:
    """Tests for the Goal dataclass."""

    def test_goal_creation(self) -> None:
        """Test creating a goal with defaults."""
        goal = Goal(name="Test Goal", target=1000)
        assert goal.name == "Test Goal"
        assert goal.target == 1000
        assert goal.current == 0
        assert goal.active is True

    def test_goal_progress_percent(self) -> None:
        """Test progress calculation."""
        goal = Goal(name="Test", target=100, current=50)
        assert goal.progress_percent() == 50.0

    def test_goal_is_achieved(self) -> None:
        """Test achievement check."""
        goal = Goal(name="Test", target=100, current=100)
        assert goal.is_achieved() is True

        goal.current = 50
        assert goal.is_achieved() is False

    def test_goal_serialization(self) -> None:
        """Test to_dict and from_dict."""
        goal = Goal(name="Serialize Test", target=500, current=250)
        data = goal.to_dict()

        restored = Goal.from_dict(data)
        assert restored.name == goal.name
        assert restored.target == goal.target
        assert restored.current == goal.current


class TestAutonomyEngine:
    """Tests for the AutonomyEngine class."""

    def test_engine_initialization(self, engine: AutonomyEngine) -> None:
        """Test engine initializes correctly."""
        assert engine.state == AutonomyState.IDLE
        assert engine.goals == []
        assert engine.client_niche == "Tech"

    def test_add_goal(self, engine: AutonomyEngine) -> None:
        """Test adding goals."""
        goal = Goal(name="Boost Engagement", metric="engagement", target=5000)
        goal_id = engine.add_goal(goal)

        assert len(engine.goals) == 1
        assert engine.goals[0].id == goal_id

    def test_remove_goal(self, engine: AutonomyEngine) -> None:
        """Test removing goals."""
        goal = Goal(name="To Remove", target=100)
        goal_id = engine.add_goal(goal)

        assert engine.remove_goal(goal_id) is True
        assert len(engine.goals) == 0

        # Removing non-existent goal
        assert engine.remove_goal("fake-id") is False

    def test_get_active_goals(self, engine: AutonomyEngine) -> None:
        """Test filtering active goals."""
        engine.add_goal(Goal(name="Active", target=100, active=True))
        engine.add_goal(Goal(name="Inactive", target=100, active=False))

        active = engine.get_active_goals()
        assert len(active) == 1
        assert active[0].name == "Active"

    def test_update_goal_progress(self, engine: AutonomyEngine) -> None:
        """Test updating goal progress."""
        goal = Goal(name="Progress Test", target=100)
        goal_id = engine.add_goal(goal)

        updated = engine.update_goal_progress(goal_id, 75)
        assert updated is not None
        assert updated.current == 75

    @patch("social_media_manager.core.autonomy.TrendRadar")
    @patch("social_media_manager.core.autonomy.RLScheduler")
    @patch("social_media_manager.core.autonomy.WorkflowPlanner")
    def test_run_daily_cycle(
        self,
        mock_planner_cls: MagicMock,
        mock_scheduler_cls: MagicMock,
        mock_radar_cls: MagicMock,
        engine: AutonomyEngine,
    ) -> None:
        """Test the daily cycle runs through all states."""
        # Setup mocks
        mock_radar_cls.return_value.check_trends.return_value = {"trend": "AI Tools"}
        mock_scheduler_cls.return_value.q_table = {}
        mock_scheduler_cls.return_value.get_best_action.return_value = ("Monday", 10)
        mock_planner_cls.return_value.create_plan.return_value = {"plan": "test"}

        result = engine.run_daily_cycle()

        assert result["success"] is True
        assert engine.state == AutonomyState.IDLE
        assert "content_plan" in result
        assert "best_time" in result

    def test_get_status(self, engine: AutonomyEngine) -> None:
        """Test status reporting."""
        engine.add_goal(Goal(name="Status Test", target=100))

        status = engine.get_status()
        assert status["state"] == "idle"
        assert status["active_goals"] == 1
        assert status["client_niche"] == "Tech"
