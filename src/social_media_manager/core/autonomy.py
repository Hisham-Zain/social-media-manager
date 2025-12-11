"""
Autonomy Engine for AgencyOS.

The "Infinite Loop" - a background daemon that runs daily cycles,
checks goals, analyzes performance, and schedules content autonomously.

Features:
- Goal-driven decision making
- Analytics-based content mode selection (viral vs. safe)
- Integration with TrendRadar and RLScheduler
- State machine: OBSERVING → DECIDING → ACTING → IDLE
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from loguru import logger

from ..ai.brain import HybridBrain
from ..ai.planner import WorkflowPlanner
from ..ai.radar import TrendRadar
from ..ai.rl_scheduler import RLScheduler
from ..database import DatabaseManager


class AutonomyState(str, Enum):
    """States for the autonomy engine state machine."""

    IDLE = "idle"
    OBSERVING = "observing"
    DECIDING = "deciding"
    ACTING = "acting"
    ERROR = "error"


@dataclass
class Goal:
    """A measurable goal for the autonomy engine."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    metric: str = "engagement"  # engagement, views, followers, posts
    target: float = 0.0
    current: float = 0.0
    deadline: str | None = None
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def progress_percent(self) -> float:
        """Calculate progress towards goal."""
        if self.target <= 0:
            return 0.0
        return min(100.0, (self.current / self.target) * 100)

    def is_achieved(self) -> bool:
        """Check if goal has been reached."""
        return self.current >= self.target

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "metric": self.metric,
            "target": self.target,
            "current": self.current,
            "deadline": self.deadline,
            "active": self.active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            name=data.get("name", ""),
            metric=data.get("metric", "engagement"),
            target=data.get("target", 0.0),
            current=data.get("current", 0.0),
            deadline=data.get("deadline"),
            active=data.get("active", True),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


class AutonomyEngine:
    """
    The Infinite Loop.

    Runs daily observe → decide → act cycles autonomously.

    Example:
        engine = AutonomyEngine(db, brain)
        engine.add_goal(Goal(name="Boost Engagement", metric="engagement", target=5000))
        result = engine.run_daily_cycle()

    Attributes:
        state: Current state machine position
        goals: Active goals driving decisions
        client_niche: Target audience/topic niche
    """

    def __init__(
        self,
        db: DatabaseManager,
        brain: HybridBrain,
        client_niche: str = "Tech",
    ) -> None:
        """
        Initialize the Autonomy Engine.

        Args:
            db: Database manager for analytics and storage.
            brain: AI brain for decision making.
            client_niche: Target niche for trend scanning.
        """
        self.db = db
        self.brain = brain
        self.client_niche = client_niche

        # AI Agents
        self.radar = TrendRadar(brain)
        self.scheduler = RLScheduler()
        self.planner = WorkflowPlanner()

        # State
        self.state = AutonomyState.IDLE
        self.goals: list[Goal] = []
        self._last_cycle_result: dict[str, Any] = {}

        logger.info("🤖 AutonomyEngine initialized")

    # --- Goal Management ---

    def add_goal(self, goal: Goal) -> str:
        """
        Add a new goal.

        Args:
            goal: Goal to add.

        Returns:
            Goal ID.
        """
        self.goals.append(goal)
        logger.info(f"📎 Goal added: {goal.name} (target: {goal.target})")
        return goal.id

    def remove_goal(self, goal_id: str) -> bool:
        """
        Remove a goal by ID.

        Args:
            goal_id: ID of goal to remove.

        Returns:
            True if removed, False if not found.
        """
        for i, g in enumerate(self.goals):
            if g.id == goal_id:
                self.goals.pop(i)
                logger.info(f"🗑️ Goal removed: {g.name}")
                return True
        return False

    def get_active_goals(self) -> list[Goal]:
        """Get all active goals."""
        return [g for g in self.goals if g.active]

    def update_goal_progress(self, goal_id: str, current: float) -> Goal | None:
        """
        Update a goal's current progress.

        Args:
            goal_id: Goal ID.
            current: New current value.

        Returns:
            Updated goal or None if not found.
        """
        for goal in self.goals:
            if goal.id == goal_id:
                goal.current = current
                if goal.is_achieved():
                    logger.success(f"🎉 Goal achieved: {goal.name}!")
                return goal
        return None

    # --- Performance Analysis ---

    def _get_performance_metrics(self, days: int = 1) -> dict[str, float]:
        """
        Fetch recent performance metrics from database.

        Args:
            days: Number of days to analyze.

        Returns:
            Dict with engagement, views, etc.
        """
        try:
            # Try to get analytics from database
            analytics = self.db.get_analytics()
            if analytics is not None and not analytics.empty:
                return {
                    "engagement": float(analytics.get("engagement", [0])[0]),
                    "views": float(analytics.get("views", [0])[0]),
                    "likes": float(analytics.get("likes", [0])[0]),
                }
        except Exception as e:
            logger.warning(f"⚠️ Failed to get analytics: {e}")

        # Fallback to zeros
        return {"engagement": 0.0, "views": 0.0, "likes": 0.0}

    def _get_engagement_target(self) -> float:
        """Get the engagement target from active goals."""
        for goal in self.get_active_goals():
            if goal.metric == "engagement":
                return goal.target
        return 100.0  # Default target

    # --- Decision Logic ---

    def _determine_content_mode(self, performance: dict[str, float]) -> str:
        """
        Decide between "viral" (risky) or "value" (safe) content.

        If engagement is below target, go high-voltage.
        Otherwise, maintain safe educational content.

        Args:
            performance: Current performance metrics.

        Returns:
            Content mode: "viral" or "value"
        """
        current_engagement = performance.get("engagement", 0)
        target = self._get_engagement_target()

        if current_engagement < target:
            logger.info(
                f"⚡ Below target ({current_engagement} < {target}): VIRAL mode"
            )
            return "viral"
        else:
            logger.info(f"📚 On target ({current_engagement} >= {target}): VALUE mode")
            return "value"

    # --- Main Cycle ---

    def run_daily_cycle(
        self,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        """
        Execute one observe → decide → act cycle.

        This is the core autonomous loop that:
        1. Observes: Checks analytics and trends
        2. Decides: Determines content mode and timing
        3. Acts: Creates content plan or schedules posts

        Args:
            progress_callback: Optional callback for progress updates.

        Returns:
            Dict with cycle results including mode, trends, and actions.
        """
        result: dict[str, Any] = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "state_history": [],
            "errors": [],
        }

        def progress(pct: float, msg: str) -> None:
            result["state_history"].append({"pct": pct, "msg": msg})
            if progress_callback:
                progress_callback(pct, msg)

        try:
            # === PHASE 1: OBSERVING ===
            self.state = AutonomyState.OBSERVING
            progress(0.1, "📡 Observing: Checking analytics...")

            performance = self._get_performance_metrics(days=1)
            result["performance"] = performance

            progress(0.2, f"📡 Observing: Scanning trends for '{self.client_niche}'...")
            trends = self.radar.check_trends(self.client_niche)
            result["trends"] = trends

            # === PHASE 2: DECIDING ===
            self.state = AutonomyState.DECIDING
            progress(0.4, "🧠 Deciding: Analyzing optimal timing...")

            # Train scheduler if Q-table is empty
            if not self.scheduler.q_table:
                self.scheduler.train(self.client_niche, episodes=5)

            best_time = self.scheduler.get_best_action()
            result["best_time"] = {"day": best_time[0], "hour": best_time[1]}

            progress(0.5, "🧠 Deciding: Determining content mode...")
            mode = self._determine_content_mode(performance)
            result["content_mode"] = mode

            # === PHASE 3: ACTING ===
            self.state = AutonomyState.ACTING
            progress(0.6, f"🎬 Acting: Creating '{mode}' content plan...")

            # Get best trend topic
            topic = "evergreen content"
            if trends and isinstance(trends, dict):
                topic = trends.get("trend", topic)

            # Create content plan
            video_info = {
                "filename": f"autonomy_{datetime.now().strftime('%Y%m%d')}",
                "duration": 60.0,
            }
            client_context = f"Mode: {mode}. Topic: {topic}. Niche: {self.client_niche}"

            plan = self.planner.create_plan(video_info, client_context)
            result["content_plan"] = plan

            progress(0.9, "✅ Cycle complete: Content plan generated")

            # Update goal progress from performance
            for goal in self.get_active_goals():
                if goal.metric in performance:
                    goal.current = performance[goal.metric]

            result["success"] = True
            self.state = AutonomyState.IDLE

        except Exception as e:
            logger.error(f"❌ Autonomy cycle failed: {e}")
            result["errors"].append(str(e))
            result["success"] = False
            self.state = AutonomyState.ERROR

        progress(1.0, "Cycle finished")
        self._last_cycle_result = result
        return result

    def get_status(self) -> dict[str, Any]:
        """
        Get current engine status.

        Returns:
            Dict with state, goals, and last cycle info.
        """
        return {
            "state": self.state.value,
            "goals": [g.to_dict() for g in self.goals],
            "active_goals": len(self.get_active_goals()),
            "client_niche": self.client_niche,
            "last_cycle": self._last_cycle_result,
        }


# --- Convenience Functions ---


def run_autonomous_cycle(
    db: DatabaseManager | None = None,
    brain: HybridBrain | None = None,
    niche: str = "Tech",
) -> dict[str, Any]:
    """
    Quick function to run a single autonomous cycle.

    Args:
        db: Optional database manager.
        brain: Optional AI brain.
        niche: Target niche.

    Returns:
        Cycle result dictionary.
    """
    if db is None:
        db = DatabaseManager()
    if brain is None:
        brain = HybridBrain()

    engine = AutonomyEngine(db, brain, client_niche=niche)
    return engine.run_daily_cycle()
