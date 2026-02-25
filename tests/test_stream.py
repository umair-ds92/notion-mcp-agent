"""
tests/test_stream.py — Tests for the /run/stream SSE endpoint.

Verifies:
  - Response content-type is text/event-stream.
  - Stream contains SSE-formatted data lines.
  - Stream ends with [DONE] sentinel.
  - Errors during streaming are surfaced as [ERROR] events, not 500s.
  - X-Request-ID header is present.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


async def _mock_stream(*messages):
    """Helper — async generator that yields the given messages."""
    for msg in messages:
        yield msg


@pytest_asyncio.fixture
async def mock_agent_pool():
    with patch("agent_pool.AgentPool.initialise", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.shutdown", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.run_task", new_callable=AsyncMock) as mock_run, \
         patch("agent_pool.AgentPool.stream_task") as mock_stream:
        mock_run.return_value = "done"
        mock_stream.return_value = _mock_stream("Message one", "Message two", "TERMINATE")
        yield mock_stream


@pytest_asyncio.fixture
async def client(mock_agent_pool):
    from app import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── SSE content type ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_returns_event_stream_content_type(client):
    response = await client.post("/run/stream", json={"task": "List pages"})
    assert "text/event-stream" in response.headers["content-type"]


# ── SSE framing ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_response_is_sse_formatted(client):
    response = await client.post("/run/stream", json={"task": "List pages"})
    assert response.status_code == 200
    # Every non-empty line should start with "data: "
    lines = [l for l in response.text.splitlines() if l.strip()]
    assert all(line.startswith("data: ") for line in lines)


@pytest.mark.asyncio
async def test_stream_ends_with_done_sentinel(client):
    response = await client.post("/run/stream", json={"task": "List pages"})
    assert "data: [DONE]" in response.text


@pytest.mark.asyncio
async def test_stream_contains_agent_messages(client):
    response = await client.post("/run/stream", json={"task": "List pages"})
    assert "Message one" in response.text
    assert "Message two" in response.text


# ── Headers ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_has_request_id_header(client):
    response = await client.post("/run/stream", json={"task": "List pages"})
    assert "x-request-id" in response.headers


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_empty_task_returns_422(client):
    response = await client.post("/run/stream", json={"task": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stream_missing_task_returns_422(client):
    response = await client.post("/run/stream", json={})
    assert response.status_code == 422


# ── Error handling ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_agent_error_surfaces_as_sse_error_event(client, mock_agent_pool):
    async def _failing_stream(task):
        raise RuntimeError("MCP crashed")
        yield  # make it an async generator

    mock_agent_pool.return_value = _failing_stream("ignored")
    response = await client.post("/run/stream", json={"task": "Do something"})
    # Error should be sent as an SSE event, not as an HTTP 500
    assert response.status_code == 200
    assert "[ERROR]" in response.text
    assert "data: [DONE]" in response.text
