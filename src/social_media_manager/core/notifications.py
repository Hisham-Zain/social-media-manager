"""
Notification System for AgencyOS.

Send notifications via email, Discord, and other channels.
"""

import json
import smtplib
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Literal

import requests
from loguru import logger

from ..config import config


@dataclass
class NotificationConfig:
    """Notification channel configuration."""

    channel: str
    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class Notification:
    """A notification to send."""

    title: str
    message: str
    level: Literal["info", "success", "warning", "error"] = "info"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class NotificationManager:
    """
    Multi-channel notification system.

    Supports:
    - Discord webhooks
    - Email (SMTP)
    - Local file logging

    Example:
        notifier = NotificationManager()

        # Configure Discord
        notifier.configure_discord(
            webhook_url="https://discord.com/api/webhooks/..."
        )

        # Send notification
        notifier.notify(
            title="Video Published!",
            message="Your video has been published.",
            level="success",
        )
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (config.BASE_DIR / "notifications")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._channels: dict[str, NotificationConfig] = {}
        self._history: list[dict[str, Any]] = []

        self._load()
        self._channels["file"] = NotificationConfig(channel="file", enabled=True)

        logger.info("🔔 Notification Manager initialized")

    def _load(self):
        """Load config from disk."""
        config_file = self.data_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)
                    for ch_data in data.get("channels", []):
                        ch = NotificationConfig(**ch_data)
                        self._channels[ch.channel] = ch
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse notification config: {e}")
            except KeyError as e:
                logger.warning(f"Invalid notification config (missing key): {e}")
            except OSError as e:
                logger.warning(f"Failed to load notification config (I/O): {e}")
            except Exception as e:
                logger.warning(
                    f"Failed to load notification config ({type(e).__name__}): {e}"
                )
                logger.debug(traceback.format_exc())

    def _save(self):
        """Save config to disk."""
        config_file = self.data_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(
                {
                    "channels": [
                        {
                            "channel": c.channel,
                            "enabled": c.enabled,
                            "settings": c.settings,
                        }
                        for c in self._channels.values()
                        if c.channel != "file"
                    ]
                },
                f,
                indent=2,
            )

    def configure_discord(self, webhook_url: str, username: str = "AgencyOS"):
        """Configure Discord notifications."""
        self._channels["discord"] = NotificationConfig(
            channel="discord",
            enabled=True,
            settings={"webhook_url": webhook_url, "username": username},
        )
        self._save()
        logger.info("✅ Discord notifications configured")

    def configure_email(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
        use_tls: bool = True,
    ):
        """Configure email notifications."""
        self._channels["email"] = NotificationConfig(
            channel="email",
            enabled=True,
            settings={
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "username": username,
                "password": password,
                "from_addr": from_addr,
                "to_addrs": to_addrs,
                "use_tls": use_tls,
            },
        )
        self._save()
        logger.info("✅ Email notifications configured")

    def notify(
        self,
        title: str,
        message: str,
        level: Literal["info", "success", "warning", "error"] = "info",
        data: dict[str, Any] | None = None,
        channels: list[str] | None = None,
    ) -> dict[str, bool]:
        """Send a notification to all configured channels."""
        notification = Notification(
            title=title, message=message, level=level, data=data or {}
        )

        results: dict[str, bool] = {}
        target_channels = channels or list(self._channels.keys())

        for channel_name in target_channels:
            channel = self._channels.get(channel_name)
            if not channel or not channel.enabled:
                continue

            try:
                if channel_name == "discord":
                    success = self._send_discord(notification)
                elif channel_name == "email":
                    success = self._send_email(notification)
                elif channel_name == "file":
                    success = self._send_file(notification)
                else:
                    success = False
                results[channel_name] = success
            except requests.exceptions.RequestException as e:
                logger.error(f"Notification network error ({channel_name}): {e}")
                results[channel_name] = False
            except KeyError as e:
                logger.error(f"Notification config missing ({channel_name}): {e}")
                results[channel_name] = False
            except Exception as e:
                logger.error(
                    f"Notification error ({channel_name}, {type(e).__name__}): {e}"
                )
                logger.debug(traceback.format_exc())
                results[channel_name] = False

        self._history.append(
            {"notification": notification.__dict__, "results": results}
        )
        return results

    def _send_discord(self, notification: Notification) -> bool:
        """Send to Discord."""
        channel = self._channels.get("discord")
        if not channel:
            return False

        colors = {
            "info": 0x3498DB,
            "success": 0x2ECC71,
            "warning": 0xF39C12,
            "error": 0xE74C3C,
        }

        payload = {
            "username": channel.settings.get("username", "AgencyOS"),
            "embeds": [
                {
                    "title": notification.title,
                    "description": notification.message,
                    "color": colors.get(notification.level, 0x3498DB),
                    "timestamp": notification.timestamp,
                }
            ],
        }

        response = requests.post(
            channel.settings["webhook_url"], json=payload, timeout=10
        )
        return 200 <= response.status_code < 300

    def _send_email(self, notification: Notification) -> bool:
        """Send via email."""
        channel = self._channels.get("email")
        if not channel:
            return False

        settings = channel.settings
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[AgencyOS] {notification.title}"
        msg["From"] = settings["from_addr"]
        msg["To"] = ", ".join(settings["to_addrs"])

        text = f"{notification.title}\n\n{notification.message}"
        msg.attach(MIMEText(text, "plain"))

        try:
            with smtplib.SMTP(settings["smtp_host"], settings["smtp_port"]) as server:
                if settings.get("use_tls", True):
                    server.starttls()
                server.login(settings["username"], settings["password"])
                server.sendmail(
                    settings["from_addr"], settings["to_addrs"], msg.as_string()
                )
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("Email auth error: Invalid credentials")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"Email connection error: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Email SMTP error: {e}")
            return False
        except OSError as e:
            logger.error(f"Email network error: {e}")
            return False
        except Exception as e:
            logger.error(f"Email error ({type(e).__name__}): {e}")
            logger.debug(traceback.format_exc())
            return False

    def _send_file(self, notification: Notification) -> bool:
        """Log to file."""
        log_file = self.data_dir / "notifications.log"
        with open(log_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": notification.timestamp,
                        "level": notification.level,
                        "title": notification.title,
                        "message": notification.message,
                    }
                )
                + "\n"
            )
        return True

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get notification history."""
        return list(reversed(self._history[-limit:]))


# Singleton
_notifier: NotificationManager | None = None


def get_notifier() -> NotificationManager:
    """Get the global notification manager."""
    global _notifier
    if _notifier is None:
        _notifier = NotificationManager()
    return _notifier


def notify(
    title: str, message: str, level: str = "info", **kwargs: Any
) -> dict[str, bool]:
    """Quick function to send a notification."""
    return get_notifier().notify(title, message, level=level, **kwargs)
