"""
notion_mcp_agent.py — Core agent logic.
Builds the AutoGen team wired to the Notion MCP server.
"""

import asyncio
from typing import AsyncIterator

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools

import config


def _build_mcp_params() -> StdioServerParams:
    return StdioServerParams(
        command="npx",
        args=["-y", "mcp-remote", config.NOTION_MCP_URL],
        env={"NOTION_API_KEY": config.NOTION_API_KEY},
        read_timeout_seconds=config.MCP_READ_TIMEOUT,
    )


async def build_team() -> RoundRobinGroupChat:
    """Initialise MCP tools and return a configured AutoGen team."""
    params = _build_mcp_params()

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

    team = RoundRobinGroupChat(
        participants=[agent],
        max_turns=config.AGENT_MAX_TURNS,
        termination_condition=TextMentionTermination("TERMINATE"),
    )

    return team


async def run_task(task: str) -> str:
    """Run a task through the agent and return the full output as a string."""
    team = await build_team()
    output = []
    async for msg in team.run_stream(task=task):
        output.append(str(msg))
    return "\n\n".join(output)


async def stream_task(task: str) -> AsyncIterator[str]:
    """Run a task and yield messages one at a time (for streaming endpoints)."""
    team = await build_team()
    async for msg in team.run_stream(task=task):
        yield str(msg)


# ── Quick local test ─────────────────────────────────────────────────────────
async def _main() -> None:
    config.validate()
    task = 'Create a new page titled "PageFromMCPNotion"'
    async for msg in stream_task(task):
        print("-" * 80)
        print(msg)


if __name__ == "__main__":
    asyncio.run(_main())
