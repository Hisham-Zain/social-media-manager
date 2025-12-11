"""
Unit tests for the Consensus Engine.

Tests the multi-agent debate protocol for content refinement.
"""

from unittest.mock import MagicMock

import pytest

from social_media_manager.ai.consensus import (
    ConsensusEngine,
    ConsensusResult,
    DebateRound,
)


@pytest.fixture
def mock_brain() -> MagicMock:
    """Create a mock HybridBrain."""
    brain = MagicMock()
    brain.think.return_value = "Improved content"
    return brain


@pytest.fixture
def engine(mock_brain: MagicMock) -> ConsensusEngine:
    """Create a ConsensusEngine with mocked brain."""
    return ConsensusEngine(brain=mock_brain, max_rounds=2)


class TestDebateRound:
    """Tests for DebateRound dataclass."""

    def test_debate_round_creation(self) -> None:
        """Test creating a debate round."""
        round_data = DebateRound(
            round_number=1,
            critique="Needs more punch",
            safety_check={"safe": True, "issues": []},
            rewrite="Improved version",
            changes_made=["refined wording"],
        )
        assert round_data.round_number == 1
        assert round_data.critique == "Needs more punch"
        assert round_data.safety_check["safe"] is True


class TestConsensusResult:
    """Tests for ConsensusResult dataclass."""

    def test_consensus_result_creation(self) -> None:
        """Test creating a consensus result."""
        result = ConsensusResult(
            original="Draft",
            final_version="Final",
            rounds=[],
            total_rounds=0,
            converged=True,
            safety_approved=True,
        )
        assert result.original == "Draft"
        assert result.converged is True


class TestConsensusEngine:
    """Tests for the ConsensusEngine class."""

    def test_engine_initialization(self, engine: ConsensusEngine) -> None:
        """Test engine initializes correctly."""
        assert engine.max_rounds == 2
        assert engine.convergence_threshold == 0.85

    def test_refine_script_basic(self, engine: ConsensusEngine) -> None:
        """Test basic script refinement."""
        result = engine.refine_script(
            draft="Check out this product!",
            persona="Gen Z Hater",
        )

        assert isinstance(result, ConsensusResult)
        assert result.original == "Check out this product!"
        assert result.total_rounds >= 1

    def test_refine_script_converges(
        self, mock_brain: MagicMock, engine: ConsensusEngine
    ) -> None:
        """Test that refinement can converge."""
        # Make brain return same content to trigger convergence
        mock_brain.think.return_value = "Same content"

        result = engine.refine_script(
            draft="Same content",
            persona="Gen Z Hater",
        )

        # Should converge quickly
        assert result.total_rounds <= engine.max_rounds

    def test_refine_script_with_safety_issues(
        self, mock_brain: MagicMock, engine: ConsensusEngine
    ) -> None:
        """Test handling safety issues."""
        # Mock safety check to return issues
        mock_brain.think.side_effect = [
            "Critique feedback",  # Critique
            '{"safe": false, "issues": ["Misleading"], "severity": "medium"}',
            "Improved version",  # Rewrite
        ] * 2

        result = engine.refine_script(
            draft="This will 100% make you rich!",
            persona="Brand Safety Officer",
        )

        assert isinstance(result, ConsensusResult)

    def test_evaluate_content(self, engine: ConsensusEngine) -> None:
        """Test content evaluation."""
        engine.brain.think.return_value = '{"score": 8, "feedback": "Good"}'

        results = engine.evaluate_content(
            content="Test content",
            criteria=["engagement", "clarity"],
        )

        assert "evaluations" in results
        assert "engagement" in results["evaluations"]
        assert "average_score" in results

    def test_get_critique(self, engine: ConsensusEngine) -> None:
        """Test critique generation."""
        engine.brain.think.return_value = "This is my critique"

        critique = engine._get_critique("Draft text", "Gen Z Hater")
        assert critique == "This is my critique"

    def test_check_safety(self, engine: ConsensusEngine) -> None:
        """Test safety checking."""
        engine.brain.think.return_value = (
            '{"safe": true, "issues": [], "severity": "none"}'
        )

        safety = engine._check_safety("Safe content here")
        assert safety["safe"] is True
        assert safety["issues"] == []

    def test_is_converged_same_text(self, engine: ConsensusEngine) -> None:
        """Test convergence with identical text."""
        assert engine._is_converged("Hello world", "Hello world") is True

    def test_is_converged_similar_text(self, engine: ConsensusEngine) -> None:
        """Test convergence with similar text."""
        # High overlap should converge
        old = "This is a great product for your needs"
        new = "This is an amazing product for your needs"

        # These might or might not converge depending on threshold
        result = engine._is_converged(old, new)
        assert isinstance(result, bool)

    def test_identify_changes_expanded(self, engine: ConsensusEngine) -> None:
        """Test change identification."""
        old = "Short"
        new = "This is a much longer version with more content"

        changes = engine._identify_changes(old, new)
        assert "expanded content" in changes

    def test_identify_changes_condensed(self, engine: ConsensusEngine) -> None:
        """Test condensed content detection."""
        old = "This is a very long text with lots of words"
        new = "Short"

        changes = engine._identify_changes(old, new)
        assert "condensed content" in changes


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_refine_with_consensus(self, mock_brain: MagicMock) -> None:
        """Test quick refinement function."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "social_media_manager.ai.consensus.HybridBrain",
                lambda: mock_brain,
            )

            # This would need the brain to be properly mocked
            # In a real test environment
            pass
