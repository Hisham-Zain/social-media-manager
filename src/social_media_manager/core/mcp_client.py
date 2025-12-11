"""
MCP (Model Context Protocol) Client for AgencyOS.

Manages connections to MCP servers and provides tool discovery/invocation
for LLM function calling. Enables AI agents to access:
- Filesystem operations
- Database queries
- Web search
- And more via MCP servers

Usage:
    from social_media_manager.core.mcp_client import MCPToolManager

    manager = MCPToolManager()
    await manager.initialize()
    tools = manager.get_tools_for_llm()
    result = await manager.call_tool("filesystem", "read_file", {"path": "..."})
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# MCP SDK imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not installed. Run: pip install 'mcp[cli]'")


@dataclass
class MCPServer:
    """Represents an MCP server configuration."""

    name: str
    command: str
    args: list[str]
    env: dict[str, str] = field(default_factory=dict)
    description: str = ""
    tools: list[dict[str, Any]] = field(default_factory=list)
    connected: bool = False


@dataclass
class MCPTool:
    """Represents a tool available from an MCP server."""

    server: str
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPToolManager:
    """
    Manages MCP server connections and tool invocation.

    Provides:
    - Server lifecycle management
    - Tool discovery across servers
    - Tool invocation with proper routing
    - LLM-compatible tool formatting
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        """
        Initialize the MCP Tool Manager.

        Args:
            config_path: Path to mcp_config.json. Defaults to project root.
        """
        self.config_path = Path(config_path) if config_path else self._find_config()
        self.servers: dict[str, MCPServer] = {}
        self.tools: dict[str, MCPTool] = {}  # tool_name -> MCPTool
        self._sessions: dict[str, ClientSession] = {}
        self._initialized = False

    def _find_config(self) -> Path:
        """Find mcp_config.json in project root."""
        # Try multiple locations
        candidates = [
            Path.cwd() / "mcp_config.json",
            Path(__file__).parent.parent.parent.parent / "mcp_config.json",
            Path.home() / ".social_media_manager" / "mcp_config.json",
        ]
        for path in candidates:
            if path.exists():
                return path
        # Default to project root even if not exists
        return Path(__file__).parent.parent.parent.parent / "mcp_config.json"

    def _expand_env_vars(self, value: str) -> str:
        """Expand ${VAR} style environment variables."""
        if not isinstance(value, str):
            return value

        import re

        pattern = r"\$\{([^}]+)\}"

        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, "")

        return re.sub(pattern, replacer, value)

    def load_config(self) -> None:
        """Load MCP server configuration from JSON file."""
        if not self.config_path.exists():
            logger.warning(f"MCP config not found: {self.config_path}")
            return

        try:
            with open(self.config_path) as f:
                config = json.load(f)

            for name, server_config in config.get("mcpServers", {}).items():
                # Expand environment variables in env dict
                env = {}
                for key, value in server_config.get("env", {}).items():
                    env[key] = self._expand_env_vars(value)

                # Expand ~ in args
                args = [
                    os.path.expanduser(arg) for arg in server_config.get("args", [])
                ]

                self.servers[name] = MCPServer(
                    name=name,
                    command=server_config.get("command", "npx"),
                    args=args,
                    env=env,
                    description=server_config.get("description", ""),
                )

            logger.info(f"📋 Loaded {len(self.servers)} MCP servers from config")

        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")

    async def initialize(self) -> None:
        """Initialize all configured MCP servers and discover tools."""
        if not MCP_AVAILABLE:
            logger.error("MCP SDK not available")
            return

        self.load_config()

        for server_name, server in self.servers.items():
            try:
                await self._connect_server(server_name, server)
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server '{server_name}': {e}")

        self._initialized = True
        logger.info(f"🔧 MCP initialized with {len(self.tools)} tools")

    async def _connect_server(self, name: str, server: MCPServer) -> None:
        """Connect to an MCP server and discover its tools."""
        # Build environment with parent env + server-specific env
        env = {**os.environ, **server.env}

        server_params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=env,
        )

        try:
            # Connect using stdio transport
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Discover tools
                    tools_result = await session.list_tools()

                    for tool in tools_result.tools:
                        tool_key = f"{name}.{tool.name}"
                        self.tools[tool_key] = MCPTool(
                            server=name,
                            name=tool.name,
                            description=tool.description or "",
                            input_schema=tool.inputSchema or {},
                        )
                        server.tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                            }
                        )

                    server.connected = True
                    logger.info(
                        f"✅ Connected to MCP server '{name}' "
                        f"({len(tools_result.tools)} tools)"
                    )

        except FileNotFoundError:
            logger.warning(
                f"MCP server '{name}' command not found: {server.command}. "
                "Ensure Node.js/npx is installed."
            )
        except Exception as e:
            logger.warning(f"MCP server '{name}' connection failed: {e}")

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool on an MCP server.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result as a dictionary
        """
        if not MCP_AVAILABLE:
            return {"error": "MCP SDK not available"}

        server = self.servers.get(server_name)
        if not server:
            return {"error": f"Unknown server: {server_name}"}

        env = {**os.environ, **server.env}
        server_params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=env,
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    result = await session.call_tool(tool_name, arguments=arguments)

                    # Parse result content
                    if result.content:
                        content = result.content[0]
                        if hasattr(content, "text"):
                            return {"result": content.text}
                        return {"result": str(content)}

                    return {"result": result.structuredContent or {}}

        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return {"error": str(e)}

    def get_tools_for_llm(self) -> list[dict[str, Any]]:
        """
        Get tools formatted for LLM function calling (OpenAI format).

        Returns:
            List of tool definitions in OpenAI function format
        """
        llm_tools = []

        for tool_key, tool in self.tools.items():
            llm_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_key.replace(
                            ".", "_"
                        ),  # filesystem.read_file -> filesystem_read_file
                        "description": f"[{tool.server}] {tool.description}",
                        "parameters": tool.input_schema,
                    },
                }
            )

        return llm_tools

    def get_tool_descriptions(self) -> str:
        """
        Get human-readable tool descriptions for prompt injection.

        Returns:
            Formatted string of available tools
        """
        if not self.tools:
            return "No MCP tools available."

        lines = ["Available MCP Tools:", ""]

        current_server = ""
        for tool_key, tool in sorted(self.tools.items()):
            if tool.server != current_server:
                current_server = tool.server
                server = self.servers.get(current_server)
                lines.append(f"## {current_server}")
                if server and server.description:
                    lines.append(f"   {server.description}")
                lines.append("")

            lines.append(f"  - {tool.name}: {tool.description}")

        return "\n".join(lines)

    def list_servers(self) -> list[dict[str, Any]]:
        """List all configured MCP servers and their status."""
        return [
            {
                "name": name,
                "description": server.description,
                "connected": server.connected,
                "tools_count": len(server.tools),
            }
            for name, server in self.servers.items()
        ]

    def list_tools(self) -> list[dict[str, Any]]:
        """List all discovered tools across servers."""
        return [
            {
                "server": tool.server,
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self.tools.values()
        ]


# Global instance (lazy-initialized)
_manager: MCPToolManager | None = None


def get_mcp_manager() -> MCPToolManager:
    """Get or create the global MCP Tool Manager."""
    global _manager
    if _manager is None:
        _manager = MCPToolManager()
    return _manager


async def initialize_mcp() -> MCPToolManager:
    """Initialize the global MCP manager."""
    manager = get_mcp_manager()
    if not manager._initialized:
        await manager.initialize()
    return manager
