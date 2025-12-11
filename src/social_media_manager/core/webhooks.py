"""
Webhook System for AgencyOS.

Handle incoming webhooks from external services and
trigger outgoing webhooks for events.
"""

import hashlib
import hmac
import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import requests
from loguru import logger

from ..config import config


@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""

    id: str
    name: str
    url: str
    events: list[str]  # Events to trigger on
    secret: str | None = None  # For signature verification
    enabled: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": self.events,
            "secret": self.secret,
            "enabled": self.enabled,
            "headers": self.headers,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebhookConfig":
        return cls(**data)


@dataclass
class WebhookEvent:
    """A webhook event to be sent."""

    event_type: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# Standard event types
EVENT_TYPES = [
    "content.created",
    "content.published",
    "content.scheduled",
    "video.rendered",
    "audio.generated",
    "ai.completed",
    "draft.saved",
    "template.applied",
    "job.completed",
    "job.failed",
]


class WebhookManager:
    """
    Manage webhooks for external integrations.

    Example:
        manager = WebhookManager()

        # Register outgoing webhook
        manager.register_webhook(
            name="Discord Notifications",
            url="https://discord.com/api/webhooks/...",
            events=["content.published", "video.rendered"],
        )

        # Trigger an event
        manager.trigger("content.published", {
            "title": "New Video",
            "platform": "youtube",
            "url": "https://..."
        })

        # Handle incoming webhook
        @manager.on("external.trigger")
        def handle_trigger(payload):
            print(f"Got trigger: {payload}")
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (config.BASE_DIR / "webhooks")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._webhooks: dict[str, WebhookConfig] = {}
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._history: list[dict[str, Any]] = []

        self._load()
        logger.info(f"🔗 Webhook Manager initialized ({len(self._webhooks)} webhooks)")

    def _load(self):
        """Load webhooks from disk."""
        webhooks_file = self.data_dir / "webhooks.json"
        if webhooks_file.exists():
            try:
                with open(webhooks_file) as f:
                    data = json.load(f)
                    for wh in data.get("webhooks", []):
                        webhook = WebhookConfig.from_dict(wh)
                        self._webhooks[webhook.id] = webhook
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse webhooks.json: {e}")
            except KeyError as e:
                logger.warning(f"Invalid webhook config (missing key): {e}")
            except OSError as e:
                logger.warning(f"Failed to load webhooks (I/O): {e}")
            except Exception as e:
                logger.warning(f"Failed to load webhooks ({type(e).__name__}): {e}")
                logger.debug(traceback.format_exc())

    def _save(self):
        """Save webhooks to disk."""
        webhooks_file = self.data_dir / "webhooks.json"
        with open(webhooks_file, "w") as f:
            json.dump(
                {"webhooks": [w.to_dict() for w in self._webhooks.values()]},
                f,
                indent=2,
            )

    def register_webhook(
        self,
        name: str,
        url: str,
        events: list[str],
        secret: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> WebhookConfig:
        """
        Register a new outgoing webhook.

        Args:
            name: Webhook name.
            url: Target URL.
            events: List of event types to trigger on.
            secret: Optional secret for signing payloads.
            headers: Optional custom headers.

        Returns:
            Created WebhookConfig.
        """
        webhook_id = hashlib.md5(f"{name}_{url}".encode()).hexdigest()[:12]

        webhook = WebhookConfig(
            id=webhook_id,
            name=name,
            url=url,
            events=events,
            secret=secret,
            headers=headers or {},
        )

        self._webhooks[webhook_id] = webhook
        self._save()

        logger.info(f"🔗 Registered webhook: {name} → {url}")
        return webhook

    def update_webhook(self, webhook_id: str, **updates: Any) -> WebhookConfig | None:
        """Update a webhook configuration."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        for key, value in updates.items():
            if hasattr(webhook, key):
                setattr(webhook, key, value)

        self._save()
        return webhook

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            self._save()
            return True
        return False

    def list_webhooks(self) -> list[WebhookConfig]:
        """List all registered webhooks."""
        return list(self._webhooks.values())

    def trigger(self, event_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Trigger an event to all registered webhooks.

        Args:
            event_type: Event type (e.g., "content.published").
            payload: Event payload data.

        Returns:
            List of delivery results.
        """
        results = []
        event = WebhookEvent(event_type=event_type, payload=payload)

        # Call local handlers
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(payload)
                except TypeError as e:
                    logger.error(f"Handler type error for {event_type}: {e}")
                except Exception as e:
                    logger.error(
                        f"Handler error for {event_type} ({type(e).__name__}): {e}"
                    )
                    logger.debug(traceback.format_exc())

        # Send to registered webhooks
        for webhook in self._webhooks.values():
            if not webhook.enabled:
                continue

            if event_type not in webhook.events and "*" not in webhook.events:
                continue

            result = self._send_webhook(webhook, event)
            results.append(result)

            # Record in history
            self._history.append(
                {
                    "webhook_id": webhook.id,
                    "event_type": event_type,
                    "timestamp": event.timestamp,
                    "success": result.get("success", False),
                }
            )

        return results

    def _send_webhook(
        self,
        webhook: WebhookConfig,
        event: WebhookEvent,
    ) -> dict[str, Any]:
        """Send a webhook request."""
        payload = {
            "event": event.event_type,
            "timestamp": event.timestamp,
            "data": event.payload,
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgencyOS/2.4",
            **webhook.headers,
        }

        # Sign payload if secret is set
        if webhook.secret:
            payload_bytes = json.dumps(payload).encode()
            signature = hmac.new(
                webhook.secret.encode(), payload_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        try:
            response = requests.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=10,
            )

            success = 200 <= response.status_code < 300

            if success:
                logger.info(f"✅ Webhook sent: {event.event_type} → {webhook.name}")
            else:
                logger.warning(
                    f"⚠️ Webhook failed: {webhook.name} (status {response.status_code})"
                )

            return {
                "success": success,
                "webhook_id": webhook.id,
                "status_code": response.status_code,
                "response": response.text[:200],
            }

        except requests.RequestException as e:
            logger.error(f"❌ Webhook error: {webhook.name} - {e}")
            return {
                "success": False,
                "webhook_id": webhook.id,
                "error": str(e),
            }

    def on(self, event_type: str) -> Callable[..., Any]:
        """
        Decorator to register an event handler.

        Example:
            @webhook_manager.on("content.published")
            def handle_published(payload):
                print(f"Published: {payload}")
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(func)
            return func

        return decorator

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent webhook history."""
        return list(reversed(self._history[-limit:]))

    def test_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Send a test event to a webhook."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        test_event = WebhookEvent(
            event_type="test.ping",
            payload={
                "message": "Test webhook from AgencyOS",
                "webhook_name": webhook.name,
            },
        )

        return self._send_webhook(webhook, test_event)


# Discord webhook helper
def create_discord_webhook(
    manager: WebhookManager,
    name: str,
    discord_url: str,
    events: list[str] | None = None,
) -> WebhookConfig:
    """
    Create a webhook configured for Discord.

    Args:
        manager: WebhookManager instance.
        name: Webhook name.
        discord_url: Discord webhook URL.
        events: Events to listen for (default: all).

    Returns:
        Created WebhookConfig.
    """
    return manager.register_webhook(
        name=name,
        url=discord_url,
        events=events or ["*"],
    )


# Singleton
_manager: WebhookManager | None = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager."""
    global _manager
    if _manager is None:
        _manager = WebhookManager()
    return _manager


def trigger_webhook(event_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Quick function to trigger webhooks."""
    return get_webhook_manager().trigger(event_type, payload)
