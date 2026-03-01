"""
tests/test_auth.py — API key authentication middleware tests.

Verifies:
  - Requests without Authorization header return 401.
  - Requests with wrong API key return 403.
  - Requests with correct API key pass through.
  - /health is publicly accessible without auth.
  - Auth is skipped entirely when API_KEY is not set.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@pytest_asyncio.fixture
async def client_with_auth():
    """Client fixture with API_KEY set to 'test-secret'."""
    with patch("agent_pool.AgentPool.initialise", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.shutdown", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.run_task", new_callable=AsyncMock) as mock_run, \
         patch("config.API_KEY", "test-secret"):
        mock_run.return_value = "done"
        from app import app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


@pytest_asyncio.fixture
async def client_no_auth():
    """Client fixture with no API_KEY set (auth disabled)."""
    with patch("agent_pool.AgentPool.initialise", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.shutdown", new_callable=AsyncMock), \
         patch("agent_pool.AgentPool.run_task", new_callable=AsyncMock) as mock_run, \
         patch("config.API_KEY", ""):
        mock_run.return_value = "done"
        from app import app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


# ── Health is always public ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_accessible_without_auth(client_with_auth):
    response = await client_with_auth.get("/health")
    assert response.status_code == 200


# ── Missing header ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_without_auth_header_returns_401(client_with_auth):
    response = await client_with_auth.post("/run", json={"task": "test"})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


# ── Wrong key ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_with_wrong_key_returns_403(client_with_auth):
    response = await client_with_auth.post(
        "/run",
        json={"task": "test"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


# ── Correct key ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_with_correct_key_passes(client_with_auth):
    response = await client_with_auth.post(
        "/run",
        json={"task": "test"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200


# ── Auth disabled ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_without_key_when_auth_disabled_passes(client_no_auth):
    response = await client_no_auth.post("/run", json={"task": "test"})
    assert response.status_code == 200


# ── Bad format ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_with_malformed_auth_header_returns_401(client_with_auth):
    response = await client_with_auth.post(
        "/run",
        json={"task": "test"},
        headers={"Authorization": "test-secret"},  # missing "Bearer "
    )
    assert response.status_code == 401