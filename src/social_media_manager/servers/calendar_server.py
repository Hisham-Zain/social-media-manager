"""
Calendar MCP Server for AgencyOS.

Provides tools for content planning around events.

Tools:
- get_upcoming_events: Fetch calendar events
- schedule_content_around_events: Plan content timing
"""

import asyncio
import os
from datetime import datetime, timedelta
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

# Google Calendar API (optional)
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    GCAL_AVAILABLE = True
except ImportError:
    GCAL_AVAILABLE = False
    logger.info("ℹ️ Google Calendar API not installed (optional)")


# Initialize server
app = Server("calendar-server") if MCP_AVAILABLE else None


def _get_calendar_service() -> Any | None:
    """Get Google Calendar service (if configured)."""
    if not GCAL_AVAILABLE:
        return None

    # Check for credentials
    creds_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS")
    if not creds_path:
        return None

    try:
        creds = Credentials.from_authorized_user_file(creds_path)
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.warning(f"⚠️ Failed to init Calendar API: {e}")
        return None


async def _get_upcoming_events(
    days_ahead: int = 7,
    calendar_id: str = "primary",
) -> list[Any]:
    """
    Get upcoming calendar events.

    Args:
        days_ahead: Number of days to look ahead.
        calendar_id: Calendar ID (default: primary).

    Returns:
        List of TextContent with events.
    """
    service = _get_calendar_service()

    # If Google Calendar not available, return mock/example events
    if not service:
        # Return simulated events for demo/testing
        mock_events = [
            {
                "summary": "Product Launch",
                "start": (datetime.now() + timedelta(days=3)).isoformat(),
                "description": "New feature release",
            },
            {
                "summary": "Weekly Team Meeting",
                "start": (datetime.now() + timedelta(days=1)).isoformat(),
                "description": "Sprint planning",
            },
            {
                "summary": "Content Review",
                "start": (datetime.now() + timedelta(days=5)).isoformat(),
                "description": "Review next week's posts",
            },
        ]

        text = f"📅 Upcoming events (next {days_ahead} days):\n\n"
        for event in mock_events:
            text += f"• {event['summary']} - {event['start'][:10]}\n"
            text += f"  {event.get('description', '')}\n"

        text += (
            "\nℹ️ (Demo data - configure GOOGLE_CALENDAR_CREDENTIALS for real events)"
        )

        return [TextContent(type="text", text=text)]

    try:
        now = datetime.utcnow().isoformat() + "Z"
        end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now,
                timeMax=end,
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            return [TextContent(type="text", text="📅 No upcoming events")]

        text = f"📅 Upcoming events (next {days_ahead} days):\n\n"
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            text += f"• {event['summary']} - {start}\n"

        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"❌ Calendar API error: {e}")
        return [TextContent(type="text", text=f"❌ Error fetching events: {e}")]


async def _schedule_content_around_events(
    days_ahead: int = 7,
) -> list[Any]:
    """
    Suggest content scheduling based on upcoming events.

    Args:
        days_ahead: Days to analyze.

    Returns:
        Content scheduling suggestions.
    """
    # Get events first
    events_result = await _get_upcoming_events(days_ahead)
    events_text = events_result[0].text if events_result else "No events"

    # Generate scheduling suggestions
    suggestions = f"""
📆 Content Scheduling Suggestions

Based on upcoming events:
{events_text}

Recommended posting schedule:
• 1-2 days before major events: Teaser content
• Day of event: Live updates / real-time engagement
• Day after: Recap / highlights
• Low-activity days: Educational / evergreen content

💡 Tip: Schedule high-engagement content for event peaks,
   and use quieter periods for value-driven posts.
"""

    return [TextContent(type="text", text=suggestions)]


if MCP_AVAILABLE and app:

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Calendar tools."""
        return [
            Tool(
                name="get_upcoming_events",
                description="Get upcoming calendar events for content planning",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days to look ahead",
                            "default": 7,
                        },
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (default: primary)",
                            "default": "primary",
                        },
                    },
                },
            ),
            Tool(
                name="schedule_content_around_events",
                description="Get content scheduling suggestions based on events",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "default": 7,
                        },
                    },
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
        """Route tool calls to handlers."""
        if name == "get_upcoming_events":
            return await _get_upcoming_events(
                arguments.get("days_ahead", 7),
                arguments.get("calendar_id", "primary"),
            )
        elif name == "schedule_content_around_events":
            return await _schedule_content_around_events(
                arguments.get("days_ahead", 7),
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
