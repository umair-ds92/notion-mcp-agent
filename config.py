"""
config.py — Centralised configuration loaded from environment variables.
All settings live here. No other file should import os.getenv() directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "o4-mini")

# ── Notion ───────────────────────────────────────────────────────────────────
NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
NOTION_MCP_URL: str = os.getenv("NOTION_MCP_URL", "https://mcp.notion.com/mcp")

# ── Agent behaviour ──────────────────────────────────────────────────────────
AGENT_MAX_TURNS: int = int(os.getenv("AGENT_MAX_TURNS", "5"))
MCP_READ_TIMEOUT: int = int(os.getenv("MCP_READ_TIMEOUT", "20"))
AGENT_SYSTEM_MESSAGE: str = (
    "You are a helpful assistant that can search, summarize, and manage "
    "content in the user's Notion workspace. "
    "Try to infer the right tool and call it to complete the task. "
    "Say TERMINATE when you are done."
)

# ── Server ───────────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", "7001"))

# ── Ngrok (optional) ─────────────────────────────────────────────────────────
NGROK_AUTH_TOKEN: str = os.getenv("NGROK_AUTH_TOKEN", "")
USE_NGROK: bool = bool(NGROK_AUTH_TOKEN)


# ── Validation ───────────────────────────────────────────────────────────────
def validate() -> None:
    """Raise at startup if required secrets are missing."""
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not NOTION_API_KEY:
        missing.append("NOTION_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values."
        )