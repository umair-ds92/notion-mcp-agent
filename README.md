# notion-mcp-agent

> Autonomous Notion workspace agent built with **Microsoft AutoGen** and **MCP (Model Context Protocol)** — interact with your Notion pages via a natural language REST API.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![CI](https://github.com/umair-ds92/notion-mcp-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/umair-ds92/notion-mcp-agent/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## How It Works

```
Client (curl / Postman)
    │ Authorization: Bearer <key>
    ├── POST /run         → full result at once
    └── POST /run/stream  → real-time SSE stream
    ▼
APIKeyMiddleware → FastAPI (app.py) :7001
    │ request_id · structured JSON logs · OTel traces
    ▼
AgentPool singleton (agent_pool.py)
    │ tools loaded once from all enabled MCP servers
    ▼
Tool Registry (tools/registry.py)
    ├── Notion MCP        (always enabled)
    ├── Gmail MCP         (opt-in: GMAIL_ENABLED=true)
    └── Google Calendar   (opt-in: GCAL_ENABLED=true)
    ▼
AutoGen AssistantAgent (OpenAI o4-mini)
    ▼
Notion Cloud / Gmail / Google Calendar
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Node.js + npx | 18+ |
| OpenAI API key | — |
| Notion integration token | — |

---

## Setup

```bash
git clone https://github.com/umair-ds92/notion-mcp-agent.git
cd notion-mcp-agent
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY and NOTION_API_KEY
```

---

## Run

```bash
# Local
python app.py

# Docker
docker compose up --build
```

Server at `http://localhost:7001` · Docs at `/docs`

---

## API

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | ❌ | Liveness check |
| POST | `/run` | ✅ | Full result at once |
| POST | `/run/stream` | ✅ | Real-time SSE stream |

```bash
curl -X POST http://localhost:7001/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"task": "Create a page titled Sprint 42 Retro"}'

# Streaming
curl -X POST http://localhost:7001/run/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"task": "List all pages"}' --no-buffer
```

> Leave `API_KEY` empty in `.env` to disable auth for local development.

---

## Adding a New Tool Integration

1. Add a new `ToolServer` entry in `tools/registry.py`
2. Add the env vars to `.env.example` and `config.py`
3. Enable it with `TOOL_NAME_ENABLED=true` in `.env`

No changes to `agent_pool.py` or `app.py` required.

---

## Test & Lint

```bash
pytest tests/ -v
ruff check .
mypy app.py
```

CI runs automatically on every push via GitHub Actions.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `NOTION_API_KEY` | ✅ | — | Notion integration token |
| `API_KEY` | ❌ | — | Bearer token (empty = auth disabled) |
| `OPENAI_MODEL` | ❌ | `o4-mini` | Model to use |
| `AGENT_MAX_TURNS` | ❌ | `5` | Max reasoning turns |
| `MCP_READ_TIMEOUT` | ❌ | `20` | MCP timeout (seconds) |
| `LOG_LEVEL` | ❌ | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `RETRY_MAX_ATTEMPTS` | ❌ | `3` | MCP retry attempts |
| `OTEL_ENABLED` | ❌ | `false` | Enable OpenTelemetry tracing |
| `OTEL_SERVICE_NAME` | ❌ | `notion-mcp-agent` | Service name in traces |
| `OTEL_EXPORTER_ENDPOINT` | ❌ | `localhost:4317` | OTLP gRPC endpoint |
| `GMAIL_ENABLED` | ❌ | `false` | Enable Gmail MCP tool |
| `GCAL_ENABLED` | ❌ | `false` | Enable Google Calendar MCP tool |
| `PORT` | ❌ | `7001` | Server port |
| `NGROK_AUTH_TOKEN` | ❌ | — | Enables public ngrok tunnel |

---

## Project Structure

```
notion-mcp-agent/
├── app.py                        # FastAPI — routes, auth, tracing
├── agent_pool.py                 # Singleton — loads from tool registry
├── auth.py                       # API key middleware
├── tracing.py                    # OpenTelemetry setup (opt-in)
├── logger.py                     # Structured JSON logger
├── retries.py                    # Exponential backoff decorator
├── config.py                     # Centralised config from .env
├── notion_mcp_agent.py           # Local CLI entry point
├── tools/
│   ├── registry.py               # Multi-tool MCP server registry
│   └── __init__.py
├── tests/
│   ├── test_api.py
│   ├── test_stream.py
│   ├── test_auth.py
│   ├── test_registry.py
│   ├── test_retries.py
│   └── test_config.py
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── ruff.toml
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

---

## Roadmap

- [x] Project scaffold and secure config
- [x] FastAPI + native async, agent singleton
- [x] Structured logging, error handling, retries
- [x] Streaming SSE, Docker, GitHub Actions CI
- [x] API key auth, OpenTelemetry tracing, multi-tool registry

---

## License

MIT © 2026