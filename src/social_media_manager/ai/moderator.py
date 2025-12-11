"""
Debate Moderator for the War Room Agent Debate System.

Orchestrates multi-round debates between AI personas to refine
content strategies through productive disagreement.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from .brain import HybridBrain
from .personas import (
    HYPE_BEAST,
    SKEPTIC,
    STRATEGIST,
    Persona,
    get_debate_prompt,
)


@dataclass
class DebateMessage:
    """A single message in the debate."""

    speaker: Persona
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    round_number: int = 0


@dataclass
class DebateResult:
    """Complete result of a debate session."""

    topic: str
    messages: list[DebateMessage]
    final_recommendation: str
    duration_seconds: float
    rounds_completed: int


class DebateModerator:
    """
    Orchestrates debates between AI personas.

    The debate follows a structured format:
    1. Hype Beast opens with viral-focused take
    2. Skeptic critiques from credibility angle
    3. Strategist synthesizes into final recommendation

    This can loop for multiple rounds if deeper exploration is needed.

    Example:
        moderator = DebateModerator()
        result = moderator.run_debate("AI ethics video for LinkedIn")
        for msg in result.messages:
            print(f"{msg.speaker.name}: {msg.content}")
    """

    def __init__(self, brain: HybridBrain | None = None) -> None:
        self.brain = brain if brain else HybridBrain()
        self._debate_history: list[DebateResult] = []

    def run_debate(
        self,
        topic: str,
        rounds: int = 1,
        on_message: Callable[[DebateMessage], Any] | None = None,
    ) -> DebateResult:
        """
        Run a structured debate on a topic.

        Args:
            topic: The content idea or strategy to debate.
            rounds: Number of full debate cycles (Hype → Skeptic → Strategist).
            on_message: Optional callback for streaming updates.

        Returns:
            DebateResult with all messages and final recommendation.
        """
        logger.info(f"🎭 War Room: Starting debate on '{topic}'")
        start_time = datetime.now()
        messages: list[DebateMessage] = []

        for round_num in range(1, rounds + 1):
            logger.info(f"  📢 Round {round_num}/{rounds}")

            # === HYPE BEAST OPENS ===
            previous = messages[-1] if messages else None
            hype_prompt = get_debate_prompt(
                HYPE_BEAST,
                topic,
                previous.content if previous else None,
                previous.speaker.name if previous else None,
            )

            hype_response = self.brain.think(hype_prompt)
            hype_msg = DebateMessage(
                speaker=HYPE_BEAST,
                content=hype_response or "No response generated.",
                round_number=round_num,
            )
            messages.append(hype_msg)
            if on_message:
                on_message(hype_msg)

            # === SKEPTIC CRITIQUES ===
            skeptic_prompt = get_debate_prompt(
                SKEPTIC,
                topic,
                hype_response,
                HYPE_BEAST.name,
            )

            skeptic_response = self.brain.think(skeptic_prompt)
            skeptic_msg = DebateMessage(
                speaker=SKEPTIC,
                content=skeptic_response or "No response generated.",
                round_number=round_num,
            )
            messages.append(skeptic_msg)
            if on_message:
                on_message(skeptic_msg)

            # === STRATEGIST SYNTHESIZES ===
            # Give strategist context from both
            strategist_context = (
                f"HYPE BEAST said:\n{hype_response}\n\n"
                f"SKEPTIC responded:\n{skeptic_response}"
            )
            strategist_prompt = get_debate_prompt(
                STRATEGIST,
                topic,
                strategist_context,
                "The Hype Beast and Skeptic",
            )

            strategist_response = self.brain.think(strategist_prompt)
            strategist_msg = DebateMessage(
                speaker=STRATEGIST,
                content=strategist_response or "No response generated.",
                round_number=round_num,
            )
            messages.append(strategist_msg)
            if on_message:
                on_message(strategist_msg)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Extract final recommendation from last Strategist message
        final_rec = messages[-1].content if messages else "No recommendation generated."

        result = DebateResult(
            topic=topic,
            messages=messages,
            final_recommendation=final_rec,
            duration_seconds=duration,
            rounds_completed=rounds,
        )

        self._debate_history.append(result)
        logger.info(
            f"✅ Debate complete in {duration:.1f}s with {len(messages)} messages"
        )

        return result

    def get_quick_take(self, topic: str, persona_role: str = "hype_beast") -> str:
        """
        Get a quick take from a single persona without full debate.

        Args:
            topic: The topic to get a take on.
            persona_role: Which persona to use.

        Returns:
            The persona's take on the topic.
        """
        from .personas import get_persona

        persona = get_persona(persona_role)
        prompt = get_debate_prompt(persona, topic)
        return self.brain.think(prompt) or ""

    def challenge(self, statement: str, challenger: str = "skeptic") -> str:
        """
        Challenge a specific statement with a persona.

        Args:
            statement: The statement to challenge.
            challenger: Which persona should challenge it.

        Returns:
            The challenge/critique.
        """
        from .personas import get_persona

        persona = get_persona(challenger)
        prompt = get_debate_prompt(
            persona,
            f"Evaluate this statement: {statement}",
            statement,
            "Someone",
        )
        return self.brain.think(prompt) or ""

    def get_history(self) -> list[DebateResult]:
        """Get all past debate results."""
        return self._debate_history.copy()

    def export_debate_md(self, result: DebateResult) -> str:
        """
        Export a debate result as markdown for documentation.

        Args:
            result: The debate result to export.

        Returns:
            Markdown-formatted debate transcript.
        """
        lines = [
            f"# War Room Debate: {result.topic}",
            "",
            f"**Duration:** {result.duration_seconds:.1f} seconds",
            f"**Rounds:** {result.rounds_completed}",
            "",
            "---",
            "",
        ]

        current_round = 0
        for msg in result.messages:
            if msg.round_number != current_round:
                current_round = msg.round_number
                lines.append(f"## Round {current_round}")
                lines.append("")

            lines.append(f"### {msg.speaker.avatar_emoji} {msg.speaker.name}")
            lines.append("")
            lines.append(msg.content)
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## 🎯 Final Recommendation",
                "",
                result.final_recommendation,
            ]
        )

        return "\n".join(lines)
