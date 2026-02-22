"""
notion_mcp_agent.py — Thin CLI entry point for local testing.

For the REST API, the agent is managed by agent_pool.py.
This file is kept for quick local runs and development testing.
"""

import asyncio
from typing import AsyncIterator

import config
from agent_pool import AgentPool


async def stream_task(task: str) -> AsyncIterator[str]:
    """Stream agent messages one at a time."""
    team = await AgentPool._build_team_direct()  # local dev: fresh team each run
    async for msg in team.run_stream(task=task):
        yield str(msg)


async def _main() -> None:
    config.validate()
    task = 'Create a new page titled "PageFromMCPNotion"'
    await AgentPool.initialise()
    result = await AgentPool.run_task(task)
    print(result)


if __name__ == "__main__":
    asyncio.run(_main())