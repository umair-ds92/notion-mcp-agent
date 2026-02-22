"""
agent_pool.py — Agent singleton / pool.

Loads MCP tools ONCE at application startup and keeps the team
ready to serve requests without re-spawning the MCP subprocess
on every call.

Why this matters:
  The original code called build_team() inside every POST /run,
  which re-ran `npx mcp-remote`, re-fetched all tool schemas, and
  re-built the model client on every single request — adding several
  seconds of cold-start overhead each time. This module fixes that.
"""

import asyncio
from typing import Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools

import config

# Module-level singleton state
_team: Optional[RoundRobinGroupChat] = None
_lock = asyncio.Lock()


async def _build_team() -> RoundRobinGroupChat:
    """Build and return a fully wired AutoGen team."""
    params = StdioServerParams(
        command="npx",
        args=["-y", "mcp-remote", config.NOTION_MCP_URL],
        env={"NOTION_API_KEY": config.NOTION_API_KEY},
        read_timeout_seconds=config.MCP_READ_TIMEOUT,
    )

    model = OpenAIChatCompletionClient(
        model=config.OPENAI_MODEL,
        api_key=config.OPENAI_API_KEY,
    )

    mcp_tools = await mcp_server_tools(server_params=params)

    agent = AssistantAgent(
        name="notion_agent",
        system_message=config.AGENT_SYSTEM_MESSAGE,
        model_client=model,
        tools=mcp_tools,
        reflect_on_tool_use=True,
    )

    return RoundRobinGroupChat(
        participants=[agent],
        max_turns=config.AGENT_MAX_TURNS,
        termination_condition=TextMentionTermination("TERMINATE"),
    )


class AgentPool:
    """
    Thin singleton wrapper around the AutoGen team.

    Usage:
        await AgentPool.initialise()   # call once at app startup
        result = await AgentPool.run_task("Create a page titled X")
        await AgentPool.shutdown()     # call on app teardown
    """

    @classmethod
    async def initialise(cls) -> None:
        """Warm up: build the team and cache it."""
        global _team
        async with _lock:
            if _team is None:
                _team = await _build_team()

    @classmethod
    async def run_task(cls, task: str) -> str:
        """
        Run a task against the cached team.
        Falls back to building the team if not yet initialised.
        """
        global _team
        if _team is None:
            await cls.initialise()

        output = []
        async for msg in _team.run_stream(task=task):
            output.append(str(msg))
        return "\n\n".join(output)

    @classmethod
    async def shutdown(cls) -> None:
        """Cleanup on application teardown."""
        global _team
        _team = None

    @classmethod
    async def _build_team_direct(cls) -> RoundRobinGroupChat:
        """Build a fresh team — for local CLI use only, bypasses the singleton."""
        return await _build_team()