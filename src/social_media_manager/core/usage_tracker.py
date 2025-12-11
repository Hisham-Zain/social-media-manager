"""
Analytics Tracker for AgencyOS.

Track AI usage costs, content performance, and generate insights.
Separate from the YouTube API AnalyticsUpdater in analytics.py.
"""

import csv
import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from ..config import config


@dataclass
class AIUsageRecord:
    """Record of AI model usage."""

    timestamp: str
    model: str
    provider: str
    operation: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "model": self.model,
            "provider": self.provider,
            "operation": self.operation,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error,
        }


# Estimated costs per 1K tokens (USD) - mostly free!
MODEL_COSTS: dict[str, dict[str, float]] = {
    # Local Ollama (FREE)
    "llama3.2:3b": {"input": 0.0, "output": 0.0},
    "llama3.2:1b": {"input": 0.0, "output": 0.0},
    "llama3.1:8b": {"input": 0.0, "output": 0.0},
    "mistral:7b": {"input": 0.0, "output": 0.0},
    # Groq (FREE tier)
    "llama-3.1-70b-versatile": {"input": 0.0, "output": 0.0},
    "llama-3.1-8b-instant": {"input": 0.0, "output": 0.0},
    "mixtral-8x7b-32768": {"input": 0.0, "output": 0.0},
    # Google (FREE tier)
    "gemini-1.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    # Paid options (for reference)
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
}


class AIUsageTracker:
    """
    Track AI model usage and costs.

    Example:
        tracker = AIUsageTracker()

        # Track usage
        tracker.track(
            model="llama3.2:3b",
            provider="ollama",
            operation="text_generation",
            input_tokens=500,
            output_tokens=200,
        )

        # Get costs summary
        costs = tracker.get_costs(days=30)
        print(f"Total: ${costs['total_cost']:.4f}")

        # Get usage by model
        usage = tracker.get_usage_by_model(days=7)
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (config.BASE_DIR / "analytics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._usage: list[AIUsageRecord] = []
        self._load()
        logger.info(f"💰 AI Usage Tracker initialized ({len(self._usage)} records)")

    def _load(self):
        """Load usage data from disk."""
        usage_file = self.data_dir / "ai_usage.json"
        if usage_file.exists():
            try:
                with open(usage_file) as f:
                    data = json.load(f)
                    self._usage = [AIUsageRecord(**r) for r in data]
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI usage data: {e}")
            except KeyError as e:
                logger.warning(f"Invalid AI usage record (missing key): {e}")
            except OSError as e:
                logger.warning(f"Failed to load AI usage (I/O): {e}")
            except Exception as e:
                logger.warning(f"Failed to load AI usage ({type(e).__name__}): {e}")
                logger.debug(traceback.format_exc())

    def _save(self):
        """Save usage data to disk."""
        usage_file = self.data_dir / "ai_usage.json"
        with open(usage_file, "w") as f:
            json.dump([r.to_dict() for r in self._usage], f, indent=2)

    def track(
        self,
        model: str,
        provider: str,
        operation: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error: str | None = None,
    ):
        """Track an AI model usage."""
        # Calculate cost
        model_key = model.lower()
        cost = 0.0
        if model_key in MODEL_COSTS:
            costs = MODEL_COSTS[model_key]
            cost = (input_tokens / 1000) * costs["input"] + (
                output_tokens / 1000
            ) * costs["output"]

        record = AIUsageRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            provider=provider,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            success=success,
            error=error,
        )

        self._usage.append(record)
        self._save()
        logger.debug(f"💰 Tracked: {model} ({operation}) - ${cost:.4f}")

    def get_costs(self, days: int = 30) -> dict[str, Any]:
        """Get cost summary for a period."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            r for r in self._usage if datetime.fromisoformat(r.timestamp) >= cutoff
        ]

        total_cost = sum(r.cost_usd for r in recent)
        total_tokens = sum(r.input_tokens + r.output_tokens for r in recent)

        # By model
        by_model: dict[str, dict[str, Any]] = {}
        for r in recent:
            if r.model not in by_model:
                by_model[r.model] = {"requests": 0, "tokens": 0, "cost": 0.0}
            by_model[r.model]["requests"] += 1
            by_model[r.model]["tokens"] += r.input_tokens + r.output_tokens
            by_model[r.model]["cost"] += r.cost_usd

        # By provider
        by_provider: dict[str, dict[str, Any]] = {}
        for r in recent:
            if r.provider not in by_provider:
                by_provider[r.provider] = {"requests": 0, "tokens": 0, "cost": 0.0}
            by_provider[r.provider]["requests"] += 1
            by_provider[r.provider]["tokens"] += r.input_tokens + r.output_tokens
            by_provider[r.provider]["cost"] += r.cost_usd

        return {
            "period_days": days,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_requests": len(recent),
            "by_model": by_model,
            "by_provider": by_provider,
            "is_free": total_cost == 0,
        }

    def get_usage_by_day(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily usage breakdown."""
        result = []
        for i in range(days):
            day = datetime.now() - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")

            day_records = [r for r in self._usage if r.timestamp.startswith(day_str)]

            result.append(
                {
                    "date": day_str,
                    "requests": len(day_records),
                    "tokens": sum(
                        r.input_tokens + r.output_tokens for r in day_records
                    ),
                    "cost": sum(r.cost_usd for r in day_records),
                }
            )

        return result

    def export_csv(self, days: int = 30) -> Path:
        """Export usage to CSV."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            r for r in self._usage if datetime.fromisoformat(r.timestamp) >= cutoff
        ]

        output = self.data_dir / f"ai_usage_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(output, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "model",
                    "provider",
                    "operation",
                    "input_tokens",
                    "output_tokens",
                    "cost_usd",
                    "latency_ms",
                ],
            )
            writer.writeheader()
            for r in recent:
                writer.writerow(
                    {
                        "timestamp": r.timestamp,
                        "model": r.model,
                        "provider": r.provider,
                        "operation": r.operation,
                        "input_tokens": r.input_tokens,
                        "output_tokens": r.output_tokens,
                        "cost_usd": r.cost_usd,
                        "latency_ms": r.latency_ms,
                    }
                )

        logger.info(f"📊 Exported AI usage to {output}")
        return output


@dataclass
class ContentMetrics:
    """Metrics for content performance."""

    content_id: str
    content_type: str
    platform: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_id": self.content_id,
            "content_type": self.content_type,
            "platform": self.platform,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "engagement_rate": self.engagement_rate,
            "created_at": self.created_at,
        }


class ContentTracker:
    """Track content performance metrics."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (config.BASE_DIR / "analytics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._content: list[ContentMetrics] = []
        self._load()

    def _load(self):
        content_file = self.data_dir / "content_metrics.json"
        if content_file.exists():
            try:
                with open(content_file) as f:
                    data = json.load(f)
                    self._content = [ContentMetrics(**r) for r in data]
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse content metrics: {e}")
            except KeyError as e:
                logger.warning(f"Invalid content metric (missing key): {e}")
            except OSError as e:
                logger.warning(f"Failed to load content metrics (I/O): {e}")
            except Exception as e:
                logger.warning(
                    f"Failed to load content metrics ({type(e).__name__}): {e}"
                )
                logger.debug(traceback.format_exc())

    def _save(self):
        content_file = self.data_dir / "content_metrics.json"
        with open(content_file, "w") as f:
            json.dump([c.to_dict() for c in self._content], f, indent=2)

    def track(self, content_id: str, content_type: str, platform: str, **metrics: Any):
        """Track or update content metrics."""
        existing = next((c for c in self._content if c.content_id == content_id), None)

        if existing:
            for key, value in metrics.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            # Recalculate engagement
            if existing.views > 0:
                total = existing.likes + existing.comments + existing.shares
                existing.engagement_rate = (total / existing.views) * 100
        else:
            content = ContentMetrics(
                content_id=content_id,
                content_type=content_type,
                platform=platform,
                **metrics,
            )
            if content.views > 0:
                total = content.likes + content.comments + content.shares
                content.engagement_rate = (total / content.views) * 100
            self._content.append(content)

        self._save()

    def get_summary(
        self, days: int = 30, platform: str | None = None
    ) -> dict[str, Any]:
        """Get content performance summary."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            c for c in self._content if datetime.fromisoformat(c.created_at) >= cutoff
        ]

        if platform:
            recent = [c for c in recent if c.platform == platform]

        if not recent:
            return {"content_count": 0, "total_views": 0, "avg_engagement": 0}

        return {
            "content_count": len(recent),
            "total_views": sum(c.views for c in recent),
            "total_likes": sum(c.likes for c in recent),
            "total_comments": sum(c.comments for c in recent),
            "avg_engagement": sum(c.engagement_rate for c in recent) / len(recent),
            "top_content": sorted(recent, key=lambda c: c.views, reverse=True)[:5],
        }


# Singleton instances
_ai_tracker: AIUsageTracker | None = None
_content_tracker: ContentTracker | None = None


def get_ai_tracker() -> AIUsageTracker:
    """Get the AI usage tracker."""
    global _ai_tracker
    if _ai_tracker is None:
        _ai_tracker = AIUsageTracker()
    return _ai_tracker


def get_content_tracker() -> ContentTracker:
    """Get the content tracker."""
    global _content_tracker
    if _content_tracker is None:
        _content_tracker = ContentTracker()
    return _content_tracker


def track_ai_usage(**kwargs: Any):
    """Quick function to track AI usage."""
    get_ai_tracker().track(**kwargs)


def track_content(**kwargs: Any):
    """Quick function to track content."""
    get_content_tracker().track(**kwargs)
