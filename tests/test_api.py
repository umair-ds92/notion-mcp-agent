"""
tests/test_api.py — API contract tests.

All tests mock AgentPool.run_task so no real OpenAI or Notion
calls are made. We test routing, request validation, response
shape, error handling, and the request_id header.
"""
import pytest_asyncio

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

# Patch AgentPool before the app is imported so lifespan doesn't fire
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest_asyncio.fixture
def mock_agent_pool():
    """Patch AgentPool so no real MCP/OpenAI calls happen."""
    with patch("agent_pool.AgentPool.initialise", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.shutdown", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.run_task", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "Task completed successfully."
        yield mock_run


@pytest_asyncio.fixture
async def client(mock_agent_pool):
    from app import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Health & root ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_root_returns_200(client):
    response = await client.get("/")
    assert response.status_code == 200


# ── POST /run — happy path ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_valid_task_returns_200(client, mock_agent_pool):
    response = await client.post("/run", json={"task": "List all pages"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["result"] == "Task completed successfully."
    assert "request_id" in body


@pytest.mark.asyncio
async def test_run_response_has_request_id_header(client):
    response = await client.post("/run", json={"task": "List all pages"})
    assert "x-request-id" in response.headers


# ── POST /run — validation errors ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_empty_task_returns_422(client):
    response = await client.post("/run", json={"task": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_missing_task_field_returns_422(client):
    response = await client.post("/run", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_no_body_returns_422(client):
    response = await client.post("/run")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_task_too_long_returns_422(client):
    response = await client.post("/run", json={"task": "x" * 2001})
    assert response.status_code == 422


# ── POST /run — agent failure ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_agent_error_returns_500(client, mock_agent_pool):
    mock_agent_pool.side_effect = RuntimeError("MCP subprocess crashed")
    response = await client.post("/run", json={"task": "Do something"})
    assert response.status_code == 500
    body = response.json()
    # Should not leak raw traceback — must be structured
    assert "request_id" in body["detail"]
    assert body["detail"]["code"] == "agent_error"
