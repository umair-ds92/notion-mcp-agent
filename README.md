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
    │ request_id attached · structured logs emitted
    ▼
AgentPool singleton  (agent_pool.py)
    │ MCP tools loaded once · retried on failure · duration logged
    ▼
AutoGen AssistantAgent
    │ OpenAI o4-mini · RoundRobinGroupChat
    ▼
Notion MCP Server  (npx mcp-remote)  ← retried up to 3× on error
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
# 1. Clone
git clone https://github.com/umair-ds92/notion-mcp-agent.git
cd notion-mcp-agent
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY and NOTION_API_KEY
```

---

## Run

```bash
python app.py
# API:  http://localhost:7001
# Docs: http://localhost:7001/docs
```

## Test

```bash
pytest tests/ -v
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

Every response includes a `request_id` for log tracing. The same ID is returned in the `X-Request-ID` response header.

---

## Logs

All logs are emitted as structured JSON to stdout — ready for ingestion by Datadog, CloudWatch, or any log aggregator.

```json
{"asctime": "2026-02-22T10:01:05", "levelname": "INFO", "name": "agent_pool", "message": "task_start", "task_preview": "Create a page titled..."}
{"asctime": "2026-02-22T10:01:09", "levelname": "INFO", "name": "agent_pool", "message": "task_complete", "duration_ms": 4132, "message_count": 6}
```

Set `LOG_LEVEL=DEBUG` in `.env` for verbose output during development.

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
| `RETRY_BASE_DELAY` | ❌ | `1.0` | Retry base delay (seconds) |
| `PORT` | ❌ | `7001` | Server port |
| `NGROK_AUTH_TOKEN` | ❌ | — | Enables public ngrok tunnel |

---

## Project Structure

```
notion-mcp-agent/
├── app.py                  # FastAPI routes + request_id middleware
├── agent_pool.py           # Agent singleton with logging & retries
├── notion_mcp_agent.py     # Local CLI entry point
├── logger.py               # Structured JSON logger
├── retries.py              # Exponential backoff decorator
├── config.py               # Centralised config from .env
├── requirements.txt
├── pytest.ini
├── tests/
│   ├── test_api.py         # API contract tests
│   ├── test_retries.py     # Retry logic unit tests
│   └── test_config.py      # Config validation tests
├── .env.example
├── .gitignore
└── README.md
```

---

## Roadmap

- [x] Project scaffold and secure config
- [x] FastAPI + native async, agent singleton
- [x] Structured logging, error handling, retries
- [ ] Streaming SSE endpoint (`/run/stream`)
- [ ] Docker + GitHub Actions CI
- [ ] API key auth + OpenTelemetry tracing
- [ ] Multi-tool registry (Gmail, Calendar, Slack)

---

## License

MIT © 2026