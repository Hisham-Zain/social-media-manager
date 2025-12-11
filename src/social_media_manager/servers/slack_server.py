"""
Slack MCP Server for AgencyOS.

Provides tools for team notifications and human escalation.

Tools:
- send_report: Post metrics/reports to a Slack channel
- alert_human: Escalate when autonomy engine needs help
- get_channel_history: Read recent messages from a channel
"""

import asyncio
import os
from typing import Any

from loguru import logger

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("⚠️ MCP not installed. Run: pip install mcp")

# Slack SDK
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    logger.warning("⚠️ slack_sdk not installed. Run: pip install slack_sdk")


# Initialize server
app = Server("slack-server") if MCP_AVAILABLE else None

# Slack client (lazy init)
_slack_client: WebClient | None = None


def _get_slack_client() -> WebClient | None:
    """Get or create Slack client."""
    global _slack_client
    if _slack_client is None and SLACK_AVAILABLE:
        token = os.getenv("SLACK_TOKEN")
        if token:
            _slack_client = WebClient(token=token)
        else:
            logger.warning("⚠️ SLACK_TOKEN not set")
    return _slack_client


async def _send_report(channel: str, metrics: dict[str, Any]) -> list[Any]:
    """
    Send a metrics report to a Slack channel.

    Args:
        channel: Slack channel ID or name.
        metrics: Dictionary of metrics to report.

    Returns:
        List of TextContent with result message.
    """
    client = _get_slack_client()
    if not client:
        return [TextContent(type="text", text="❌ Slack client not available")]

    try:
        # Format metrics as blocks
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📊 AgencyOS Daily Report"},
            },
            {"type": "divider"},
        ]

        for key, value in metrics.items():
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{key}:* {value}"},
                }
            )

        response = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text="AgencyOS Daily Report",
        )

        return [
            TextContent(
                type="text",
                text=f"✅ Report sent to #{channel} (ts: {response['ts']})",
            )
        ]

    except SlackApiError as e:
        logger.error(f"❌ Slack API error: {e.response['error']}")
        return [TextContent(type="text", text=f"❌ Slack error: {e.response['error']}")]


async def _alert_human(
    message: str,
    urgency: str = "medium",
) -> list[Any]:
    """
    Alert a human when autonomy engine needs intervention.

    Args:
        message: Alert message.
        urgency: "low", "medium", or "high".

    Returns:
        List of TextContent with result.
    """
    client = _get_slack_client()
    channel = os.getenv("SLACK_CHANNEL", "general")

    if not client:
        return [TextContent(type="text", text="❌ Slack client not available")]

    try:
        # Urgency emoji mapping
        emoji_map = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
        }
        emoji = emoji_map.get(urgency, "⚠️")

        response = client.chat_postMessage(
            channel=channel,
            text=f"{emoji} *AgencyOS Alert ({urgency.upper()})*\n\n{message}",
        )

        return [
            TextContent(
                type="text",
                text=f"✅ Human alerted in #{channel}",
            )
        ]

    except SlackApiError as e:
        logger.error(f"❌ Slack API error: {e.response['error']}")
        return [TextContent(type="text", text=f"❌ Slack error: {e.response['error']}")]


async def _get_channel_history(
    channel: str,
    limit: int = 10,
) -> list[Any]:
    """
    Get recent messages from a channel.

    Args:
        channel: Channel ID.
        limit: Number of messages to retrieve.

    Returns:
        List of TextContent with messages.
    """
    client = _get_slack_client()
    if not client:
        return [TextContent(type="text", text="❌ Slack client not available")]

    try:
        response = client.conversations_history(channel=channel, limit=limit)
        messages = response.get("messages", [])

        text = f"📜 Last {len(messages)} messages from #{channel}:\n\n"
        for msg in messages:
            user = msg.get("user", "unknown")
            content = msg.get("text", "")[:100]
            text += f"• [{user}]: {content}\n"

        return [TextContent(type="text", text=text)]

    except SlackApiError as e:
        return [TextContent(type="text", text=f"❌ Error: {e.response['error']}")]


if MCP_AVAILABLE and app:

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Slack tools."""
        return [
            Tool(
                name="send_report",
                description="Send a metrics report to a Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Slack channel ID or name",
                        },
                        "metrics": {
                            "type": "object",
                            "description": "Dictionary of metrics to report",
                        },
                    },
                    "required": ["channel", "metrics"],
                },
            ),
            Tool(
                name="alert_human",
                description="Alert a human when the autonomy engine needs help",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Alert message",
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "default": "medium",
                        },
                    },
                    "required": ["message"],
                },
            ),
            Tool(
                name="get_channel_history",
                description="Get recent messages from a Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["channel"],
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
        """Route tool calls to handlers."""
        if name == "send_report":
            return await _send_report(arguments["channel"], arguments["metrics"])
        elif name == "alert_human":
            return await _alert_human(
                arguments["message"],
                arguments.get("urgency", "medium"),
            )
        elif name == "get_channel_history":
            return await _get_channel_history(
                arguments["channel"],
                arguments.get("limit", 10),
            )
        else:
            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]


async def main() -> None:
    """Run the MCP server."""
    if not MCP_AVAILABLE:
        logger.error("❌ MCP not available")
        return

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
