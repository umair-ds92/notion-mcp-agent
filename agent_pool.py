"""
agent_pool.py — Agent singleton with streaming support.

Changes:
  - Added stream_task() — an async generator that yields agent
    messages one at a time, used by the /run/stream SSE endpoint.
"""

import asyncio
import time
from typing import AsyncIterator, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools

import config
from logger import get_logger
from retries import with_retry

log = get_logger(__name__)

_team: Optional[RoundRobinGroupChat] = None
_lock = asyncio.Lock()


@with_retry(max_attempts=3, base_delay=1.0, max_delay=8.0)
async def _load_mcp_tools(params: StdioServerParams):
    return await mcp_server_tools(server_params=params)


async def _build_team() -> RoundRobinGroupChat:
    log.info("agent_pool_build_start", extra={"model": config.OPENAI_MODEL})

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

    tools = await _load_mcp_tools(params)
    log.info("mcp_tools_loaded", extra={"tool_count": len(tools)})

    agent = AssistantAgent(
        name="notion_agent",
        system_message=config.AGENT_SYSTEM_MESSAGE,
        model_client=model,
        tools=tools,
        reflect_on_tool_use=True,
    )

    team = RoundRobinGroupChat(
        participants=[agent],
        max_turns=config.AGENT_MAX_TURNS,
        termination_condition=TextMentionTermination("TERMINATE"),
    )

    log.info("agent_pool_build_complete")
    return team


class AgentPool:
    """
    Singleton wrapper around the AutoGen team.

    Public methods:
        initialise()            — warm up at app startup
        run_task(task)          — run and return full result
        stream_task(task)       — async generator, yields messages one by one
        shutdown()              — cleanup on app teardown
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
        """Run a task and return the full output as a single string."""
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
        """
        Async generator — yields agent messages one at a time.
        Used by the /run/stream SSE endpoint.
        """
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
        """Build a fresh team — for local CLI use only."""
        return await _build_team()