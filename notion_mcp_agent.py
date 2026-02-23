"""
notion_mcp_agent.py — Thin CLI entry point for local testing.

For the REST API, the agent is managed by agent_pool.py.
This file is kept for quick local runs and development testing.
"""

import asyncio

import config
from agent_pool import AgentPool
from logger import get_logger

log = get_logger(__name__)


async def _main() -> None:
    config.validate()
    task = 'Create a new page titled "PageFromMCPNotion"'
    log.info("cli_run_start", task=task)
    await AgentPool.initialise()
    result = await AgentPool.run_task(task)
    log.info("cli_run_complete")
    print(result)


if __name__ == "__main__":
    asyncio.run(_main())