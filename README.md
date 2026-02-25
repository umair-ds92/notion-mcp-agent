# notion-mcp-agent

> Autonomous Notion workspace agent built with **Microsoft AutoGen** and **MCP (Model Context Protocol)** — interact with your Notion pages via a natural language REST API.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![CI](https://github.com/umair-ds92/notion-mcp-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/umair-ds92/notion-mcp-agent/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## How It Works

```
Client (curl / Postman)
    │
    ├── POST /run         → full result returned at once
    └── POST /run/stream  → messages streamed via SSE in real time
    ▼
FastAPI REST API  (app.py)  :7001
    │ request_id · structured logs · retries
    ▼
AgentPool singleton  (agent_pool.py)
    │ MCP tools loaded once at startup
    ▼
AutoGen AssistantAgent  (OpenAI o4-mini)
    ▼
Notion MCP Server  (npx mcp-remote)
    ▼
Notion Cloud  (your workspace)
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

Server starts at `http://localhost:7001` · Swagger docs at `/docs`

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/run` | Full result returned at once |
| POST | `/run/stream` | Real-time SSE stream of agent messages |

**Standard request:**
```bash
curl -X POST http://localhost:7001/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a page titled Sprint 42 Retro"}'
```

**Streaming request:**
```bash
curl -X POST http://localhost:7001/run/stream \
  -H "Content-Type: application/json" \
  -d '{"task": "Create a page titled Sprint 42 Retro"}' \
  --no-buffer
```

The stream emits one `data: <message>` SSE event per agent turn, ending with `data: [DONE]`.

---

## Test & Lint

```bash
pytest tests/ -v       # run all tests
ruff check .           # lint
mypy app.py            # type check
```

CI runs automatically on every push via GitHub Actions.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `NOTION_API_KEY` | ✅ | — | Notion integration token |
| `OPENAI_MODEL` | ❌ | `o4-mini` | Model to use |
| `AGENT_MAX_TURNS` | ❌ | `5` | Max reasoning turns |
| `MCP_READ_TIMEOUT` | ❌ | `20` | MCP timeout (seconds) |
| `LOG_LEVEL` | ❌ | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `RETRY_MAX_ATTEMPTS` | ❌ | `3` | MCP retry attempts |
| `PORT` | ❌ | `7001` | Server port |
| `NGROK_AUTH_TOKEN` | ❌ | — | Enables public ngrok tunnel |

---

## Project Structure

```
notion-mcp-agent/
├── app.py                        # FastAPI routes incl. /run/stream
├── agent_pool.py                 # Singleton with run_task + stream_task
├── notion_mcp_agent.py           # Local CLI entry point
├── logger.py                     # Structured JSON logger
├── retries.py                    # Exponential backoff decorator
├── config.py                     # Centralised config from .env
├── requirements.txt
├── ruff.toml                     # Linting config
├── pytest.ini
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .github/
│   └── workflows/
│       └── ci.yml                # GitHub Actions — lint, test, docker build
├── tests/
│   ├── test_api.py
│   ├── test_stream.py            # SSE streaming tests
│   ├── test_retries.py
│   └── test_config.py
├── .env.example
├── .gitignore
└── README.md
```

---

## Roadmap

- [x] Project scaffold and secure config
- [x] FastAPI + native async, agent singleton
- [x] Structured logging, error handling, retries
- [x] Streaming SSE endpoint, Docker, GitHub Actions CI
- [ ] API key auth + OpenTelemetry tracing
- [ ] Multi-tool registry (Gmail, Calendar, Slack)

---

## License

MIT © 2026