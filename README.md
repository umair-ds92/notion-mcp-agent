# notion-mcp-agent

> Autonomous Notion workspace agent built with **Microsoft AutoGen** and **MCP (Model Context Protocol)** — interact with your Notion pages via a natural language REST API.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## How It Works

```
Client (curl / Postman)
    │ POST /run {"task": "..."}
    ▼
FastAPI REST API  (app.py)  :7001
    │ await AgentPool.run_task(task)
    ▼
AgentPool singleton  (agent_pool.py)
    │ MCP tools loaded ONCE at startup · reused across all requests
    ▼
AutoGen AssistantAgent  (notion_mcp_agent.py)
    │ OpenAI o4-mini · RoundRobinGroupChat
    ▼
Notion MCP Server  (npx mcp-remote)
    │ create_page · search · list_databases · update_page …
    ▼
Notion Cloud  (your workspace)
```

Config flow: `.env` → `config.py` → `app.py` + `agent_pool.py`

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Node.js + npx | 18+ |
| OpenAI API key | — |
| Notion integration token | — |

> Node.js is required because the Notion MCP server runs as a subprocess via `npx mcp-remote`.

---

## Setup

```bash
# 1. Clone
git clone https://github.com/umair-ds92/notion-mcp-agent.git
cd notion-mcp-agent

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install deps
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env             # then open .env and fill in your keys
```

**Connect Notion:** Go to [developers.notion.com](https://developers.notion.com) → New integration → copy the token into `NOTION_API_KEY`. Then share your target pages with the integration via the **···** menu in Notion.

---

## Run

```bash
python app.py
# Server starts at http://localhost:7001
# Interactive API docs at http://localhost:7001/docs
```

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/run` | Submit a natural language task |

```bash
curl -X POST http://localhost:7001/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a page titled Sprint 42 Retro"}'
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `NOTION_API_KEY` | ✅ | — | Notion integration token |
| `OPENAI_MODEL` | ❌ | `o4-mini` | Model to use |
| `AGENT_MAX_TURNS` | ❌ | `5` | Max reasoning turns |
| `MCP_READ_TIMEOUT` | ❌ | `20` | MCP timeout (seconds) |
| `PORT` | ❌ | `7001` | Server port |
| `NGROK_AUTH_TOKEN` | ❌ | — | Enables public ngrok tunnel |

---

## Project Structure

```
notion-mcp-agent/
├── app.py                  # FastAPI REST API
├── agent_pool.py           # Agent singleton — MCP tools loaded once
├── notion_mcp_agent.py     # Local CLI entry point for dev/testing
├── config.py               # Centralised config from .env
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Roadmap

- [x] Project scaffold and secure config
- [x] FastAPI + native async, agent singleton
- [ ] Structured logging & retry logic
- [ ] Streaming SSE endpoint (`/run/stream`)
- [ ] Docker + GitHub Actions CI
- [ ] API key auth + OpenTelemetry tracing
- [ ] Multi-tool registry (Gmail, Calendar, Slack)

---

## License

MIT © 2026