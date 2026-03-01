"""
tools/registry.py — Multi-tool MCP registry.

Replaces the hardcoded Notion MCP config in agent_pool.py with a
registry that can load multiple MCP tool servers from config.

Each tool entry in TOOL_REGISTRY defines one MCP server. The agent
receives the combined tools from ALL enabled servers, making it
trivial to add Gmail, Google Calendar, Slack, or any other MCP
server without touching agent_pool.py.

To add a new tool server:
    1. Add a new entry to TOOL_REGISTRY below.
    2. Set the corresponding env vars in .env.
    3. That's it — the agent picks it up on next startup.

Current registry:
    notion   — Notion workspace (always enabled)
    gmail    — Gmail (enabled if GMAIL_ENABLED=true)
    calendar — Google Calendar (enabled if GCAL_ENABLED=true)
"""

from dataclasses import dataclass, field
from typing import Optional

from autogen_ext.tools.mcp import StdioServerParams

import config
from logger import get_logger

log = get_logger(__name__)


@dataclass
class ToolServer:
    """Represents one MCP tool server."""
    name: str
    params: StdioServerParams
    enabled: bool = True
    description: str = ""


def _build_registry() -> list[ToolServer]:
    """Build the list of enabled tool servers from config."""
    servers = []

    # ── Notion (always enabled) ───────────────────────────────────────────────
    servers.append(ToolServer(
        name="notion",
        description="Notion workspace — create, search, and update pages",
        params=StdioServerParams(
            command="npx",
            args=["-y", "mcp-remote", config.NOTION_MCP_URL],
            env={"NOTION_API_KEY": config.NOTION_API_KEY},
            read_timeout_seconds=config.MCP_READ_TIMEOUT,
        ),
        enabled=True,
    ))

    # ── Gmail (optional) ──────────────────────────────────────────────────────
    if config.GMAIL_ENABLED:
        servers.append(ToolServer(
            name="gmail",
            description="Gmail — read, search, and send emails",
            params=StdioServerParams(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-gmail"],
                env={"GMAIL_CREDENTIALS": config.GMAIL_CREDENTIALS},
                read_timeout_seconds=config.MCP_READ_TIMEOUT,
            ),
            enabled=True,
        ))

    # ── Google Calendar (optional) ────────────────────────────────────────────
    if config.GCAL_ENABLED:
        servers.append(ToolServer(
            name="google_calendar",
            description="Google Calendar — read and create events",
            params=StdioServerParams(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-google-calendar"],
                env={"GCAL_CREDENTIALS": config.GCAL_CREDENTIALS},
                read_timeout_seconds=config.MCP_READ_TIMEOUT,
            ),
            enabled=True,
        ))

    enabled = [s.name for s in servers if s.enabled]
    log.info("tool_registry_built", extra={"enabled_tools": enabled})
    return [s for s in servers if s.enabled]


# Module-level registry — built once on import
TOOL_REGISTRY: list[ToolServer] = _build_registry()