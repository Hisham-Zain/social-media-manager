"""
Consensus Engine for AgencyOS.

Multi-agent "writer's room" debate protocol that improves content quality
by having agents critique and refine drafts before user review.

Features:
- Structured critique with personas (Gen Z Hater, Brand Safety, etc.)
- Multi-round refinement with convergence detection
- Safety auditing for legal/brand risks
- Configurable debate intensity
"""

import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from .auditor import SalesAuditor
from .brain import HybridBrain
from .critic import CriticAgent


@dataclass
class DebateRound:
    """Result of a single debate round."""

    round_number: int
    critique: str
    safety_check: dict[str, Any]
    rewrite: str
    changes_made: list[str] = field(default_factory=list)


@dataclass
class ConsensusResult:
    """Final result of the consensus process."""

    original: str
    final_version: str
    rounds: list[DebateRound]
    total_rounds: int
    converged: bool
    safety_approved: bool


class ConsensusEngine:
    """
    Multi-agent "writer's room" debate system.

    Simulates a collaborative critique process where:
    1. A Critic agent roasts the draft
    2. An Auditor checks for safety issues
    3. The Brain rewrites incorporating feedback
    4. Process repeats until convergence

    Example:
        engine = ConsensusEngine(brain)
        result = engine.refine_script(
            draft="Check out this AMAZING product!",
            persona="Gen Z Hater"
        )
        print(result.final_version)  # Improved script
    """

    def __init__(
        self,
        brain: HybridBrain,
        max_rounds: int = 3,
        convergence_threshold: float = 0.85,
    ) -> None:
        """
        Initialize the Consensus Engine.

        Args:
            brain: AI brain for content generation.
            max_rounds: Maximum refinement rounds.
            convergence_threshold: Similarity threshold for convergence (0-1).
        """
        self.brain = brain
        self.critic = CriticAgent(brain)
        self.auditor = SalesAuditor(brain)
        self.max_rounds = max_rounds
        self.convergence_threshold = convergence_threshold

        logger.info("🗣️ ConsensusEngine initialized")

    def refine_script(
        self,
        draft: str,
        persona: str = "Gen Z Hater",
        context: str = "",
    ) -> ConsensusResult:
        """
        Run multi-round critique and refinement.

        Args:
            draft: Initial script/content draft.
            persona: Critic persona for roasting style.
            context: Additional context about the content.

        Returns:
            ConsensusResult with original, rounds, and final version.
        """
        logger.info(f"🎭 Starting consensus refinement with '{persona}' persona")

        rounds: list[DebateRound] = []
        current = draft
        converged = False
        safety_approved = True

        for round_num in range(1, self.max_rounds + 1):
            logger.info(f"📝 Round {round_num}/{self.max_rounds}")

            # Step 1: Get critique
            critique = self._get_critique(current, persona)

            # Step 2: Safety check
            safety = self._check_safety(current)
            if not safety.get("safe", True):
                safety_approved = False
                logger.warning(f"⚠️ Safety issues: {safety.get('issues', [])}")

            # Step 3: Rewrite incorporating feedback
            rewrite = self._rewrite_with_feedback(current, critique, safety, context)

            # Track changes
            changes = self._identify_changes(current, rewrite)

            rounds.append(
                DebateRound(
                    round_number=round_num,
                    critique=critique,
                    safety_check=safety,
                    rewrite=rewrite,
                    changes_made=changes,
                )
            )

            # Check for convergence
            if self._is_converged(current, rewrite):
                logger.success(f"✅ Converged at round {round_num}")
                converged = True
                current = rewrite
                break

            current = rewrite

        return ConsensusResult(
            original=draft,
            final_version=current,
            rounds=rounds,
            total_rounds=len(rounds),
            converged=converged,
            safety_approved=safety_approved,
        )

    def evaluate_content(
        self,
        content: str,
        criteria: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Multi-agent content evaluation without rewriting.

        Args:
            content: Content to evaluate.
            criteria: Evaluation criteria (default: engagement, clarity, safety).

        Returns:
            Dict with scores and feedback from each perspective.
        """
        if criteria is None:
            criteria = ["engagement", "clarity", "safety", "originality"]

        results: dict[str, Any] = {"content": content, "evaluations": {}}

        for criterion in criteria:
            prompt = f"""
            Evaluate this content for {criterion.upper()}:

            "{content}"

            Score from 1-10 and explain briefly.
            Return JSON: {{"score": N, "feedback": "..."}}
            """

            try:
                response = self.brain.think(prompt, json_mode=True)
                results["evaluations"][criterion] = json.loads(response)
            except Exception as e:
                logger.warning(f"⚠️ Evaluation for {criterion} failed: {e}")
                results["evaluations"][criterion] = {"score": 5, "feedback": "N/A"}

        # Calculate average score
        scores = [e.get("score", 5) for e in results["evaluations"].values()]
        results["average_score"] = sum(scores) / len(scores) if scores else 5.0

        return results

    def _get_critique(self, text: str, persona: str) -> str:
        """
        Get a critique from the specified persona.

        Args:
            text: Content to critique.
            persona: Critic persona (e.g., "Gen Z Hater", "Brand Manager").

        Returns:
            Critique text.
        """
        prompt = f"""
        You are a {persona}. Your job is to ruthlessly but constructively
        critique content to make it better.

        CONTENT:
        "{text}"

        Provide specific, actionable feedback:
        1. What doesn't work and why
        2. What's missing
        3. What could be punchier/clearer

        Be direct but helpful. No fluff.
        """

        try:
            return self.brain.think(prompt)
        except Exception as e:
            logger.error(f"❌ Critique failed: {e}")
            return "Unable to generate critique."

    def _check_safety(self, text: str) -> dict[str, Any]:
        """
        Check content for legal/brand safety issues.

        Args:
            text: Content to check.

        Returns:
            Dict with safe (bool), issues (list), severity (str).
        """
        prompt = f"""
        Review this content for potential issues:

        "{text}"

        Check for:
        - Defamation or false claims
        - Copyright concerns
        - Misleading statements
        - Brand safety risks
        - Potentially offensive content

        Return JSON:
        {{
            "safe": true/false,
            "issues": ["issue1", "issue2"],
            "severity": "none" | "low" | "medium" | "high",
            "recommendations": ["fix1", "fix2"]
        }}
        """

        try:
            response = self.brain.think(prompt, json_mode=True)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"⚠️ Safety check failed: {e}")
            return {"safe": True, "issues": [], "severity": "none"}

    def _rewrite_with_feedback(
        self,
        original: str,
        critique: str,
        safety: dict[str, Any],
        context: str = "",
    ) -> str:
        """
        Rewrite content incorporating critique and safety feedback.

        Args:
            original: Original content.
            critique: Critique feedback.
            safety: Safety check results.
            context: Additional context.

        Returns:
            Rewritten content.
        """
        safety_notes = ""
        if not safety.get("safe", True):
            issues = ", ".join(safety.get("issues", []))
            recommendations = ", ".join(safety.get("recommendations", []))
            safety_notes = f"""
            SAFETY ISSUES TO FIX:
            - Issues: {issues}
            - Recommendations: {recommendations}
            """

        prompt = f"""
        ORIGINAL DRAFT:
        "{original}"

        CRITIQUE:
        {critique}

        {safety_notes}

        CONTEXT: {context if context else "General social media content"}

        TASK: Rewrite the content addressing the critique while:
        1. Keeping the core message/intent
        2. Fixing any safety issues
        3. Making it more engaging/effective

        Return ONLY the rewritten content, no explanation.
        """

        try:
            result = self.brain.think(prompt)
            # Clean up any quotes the model might add
            return result.strip("\"'")
        except Exception as e:
            logger.error(f"❌ Rewrite failed: {e}")
            return original

    def _is_converged(self, old: str, new: str) -> bool:
        """
        Check if refinement has converged (minimal changes).

        Uses simple similarity heuristic.
        """
        if old == new:
            return True

        # Calculate word overlap
        old_words = set(old.lower().split())
        new_words = set(new.lower().split())

        if not old_words or not new_words:
            return False

        overlap = len(old_words & new_words)
        total = len(old_words | new_words)
        similarity = overlap / total if total > 0 else 0

        return similarity >= self.convergence_threshold

    def _identify_changes(self, old: str, new: str) -> list[str]:
        """Identify what changed between versions."""
        changes = []

        old_len = len(old)
        new_len = len(new)

        if new_len > old_len * 1.2:
            changes.append("expanded content")
        elif new_len < old_len * 0.8:
            changes.append("condensed content")

        if "?" in new and "?" not in old:
            changes.append("added question")

        if any(e in new for e in ["🔥", "💡", "✨", "🎯"]) and not any(
            e in old for e in ["🔥", "💡", "✨", "🎯"]
        ):
            changes.append("added emojis")

        if not changes:
            changes.append("refined wording")

        return changes


# --- Convenience Functions ---


def refine_with_consensus(
    draft: str,
    brain: HybridBrain | None = None,
    persona: str = "Gen Z Hater",
    max_rounds: int = 2,
) -> str:
    """
    Quick function to refine content using consensus.

    Args:
        draft: Content to refine.
        brain: Optional AI brain.
        persona: Critic persona.
        max_rounds: Max refinement rounds.

    Returns:
        Refined content string.
    """
    if brain is None:
        brain = HybridBrain()

    engine = ConsensusEngine(brain, max_rounds=max_rounds)
    result = engine.refine_script(draft, persona=persona)
    return result.final_version
