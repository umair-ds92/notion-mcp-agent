"""
agent_pool.py — Agent singleton using the multi-tool registry.

Changes from Commit 4:
  - Loads MCP tools from tools/registry.py instead of hardcoding
    the Notion server directly. Tools from ALL enabled servers are
    merged and passed to the agent in a single list.
"""

import asyncio
import time
from typing import AsyncIterator, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import mcp_server_tools

import config
from logger import get_logger
from retries import with_retry
from tools.registry import TOOL_REGISTRY

log = get_logger(__name__)

_team: Optional[RoundRobinGroupChat] = None
_lock = asyncio.Lock()


@with_retry(max_attempts=3, base_delay=1.0, max_delay=8.0)
async def _load_tools_from_server(server):
    """Load tools from a single MCP server with retry."""
    tools = await mcp_server_tools(server_params=server.params)
    log.info("tools_loaded", extra={"server": server.name, "count": len(tools)})
    return tools


async def _build_team() -> RoundRobinGroupChat:
    """Build the AutoGen team with tools from all registered MCP servers."""
    log.info("agent_pool_build_start", extra={"model": config.OPENAI_MODEL})

    # Load tools from all enabled servers concurrently
    tool_lists = await asyncio.gather(*[
        _load_tools_from_server(server) for server in TOOL_REGISTRY
    ])

    # Flatten into a single list
    all_tools = [tool for tool_list in tool_lists for tool in tool_list]
    log.info("all_tools_loaded", extra={"total_tool_count": len(all_tools)})

    model = OpenAIChatCompletionClient(
        model=config.OPENAI_MODEL,
        api_key=config.OPENAI_API_KEY,
    )

    agent = AssistantAgent(
        name="notion_agent",
        system_message=config.AGENT_SYSTEM_MESSAGE,
        model_client=model,
        tools=all_tools,
        reflect_on_tool_use=True,
    )

    team = RoundRobinGroupChat(
        participants=[agent],
        max_turns=config.AGENT_MAX_TURNS,
        termination_condition=TextMentionTermination("TERMINATE"),
    )

    log.info("agent_pool_build_complete", extra={"tool_count": len(all_tools)})
    return team


class AgentPool:
    """
    Singleton wrapper around the AutoGen team.

    Public methods:
        initialise()        — warm up at app startup
        run_task(task)      — run and return full result
        stream_task(task)   — async generator, yields messages one by one
        shutdown()          — cleanup on app teardown
    """

    @classmethod
    async def initialise(cls) -> None:
        global _team
        async with _lock:
            if _team is None:
                log.info("agent_pool_initialising")
                _team = await _build_team()
                log.info("agent_pool_ready")

    @classmethod
    async def run_task(cls, task: str) -> str:
        global _team
        if _team is None:
            await cls.initialise()

        log.info("task_start", extra={"task_preview": task[:80]})
        t0 = time.monotonic()
        output = []

        try:
            async for msg in _team.run_stream(task=task):
                output.append(str(msg))
        except Exception as exc:
            log.error("task_failed", extra={"error": str(exc), "task_preview": task[:80]})
            raise

        duration_ms = round((time.monotonic() - t0) * 1000)
        log.info("task_complete", extra={"duration_ms": duration_ms, "message_count": len(output)})
        return "\n\n".join(output)

    @classmethod
    async def stream_task(cls, task: str) -> AsyncIterator[str]:
        global _team
        if _team is None:
            await cls.initialise()

        log.info("stream_task_start", extra={"task_preview": task[:80]})
        t0 = time.monotonic()
        count = 0

        async for msg in _team.run_stream(task=task):
            count += 1
            yield str(msg)

        duration_ms = round((time.monotonic() - t0) * 1000)
        log.info("stream_task_complete", extra={"duration_ms": duration_ms, "message_count": count})

    @classmethod
    async def shutdown(cls) -> None:
        global _team
        log.info("agent_pool_shutdown")
        _team = None

    @classmethod
    async def _build_team_direct(cls) -> RoundRobinGroupChat:
        return await _build_team()