"""
tests/test_retries.py — Unit tests for the retry decorator.

Tests verify:
  - Successful calls pass through without retrying.
  - Failing calls are retried the correct number of times.
  - Non-retryable exceptions propagate immediately.
  - The final exception is re-raised after exhausting attempts.
"""

import pytest
from unittest.mock import AsyncMock, call
from retries import with_retry


# ── Success path ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_success_on_first_attempt():
    mock_fn = AsyncMock(return_value="ok")
    decorated = with_retry(max_attempts=3)(mock_fn)
    result = await decorated()
    assert result == "ok"
    assert mock_fn.call_count == 1


# ── Retry path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retries_on_failure_then_succeeds():
    mock_fn = AsyncMock(side_effect=[RuntimeError("fail"), RuntimeError("fail"), "ok"])
    decorated = with_retry(max_attempts=3, base_delay=0)(mock_fn)
    result = await decorated()
    assert result == "ok"
    assert mock_fn.call_count == 3


@pytest.mark.asyncio
async def test_raises_after_max_attempts():
    mock_fn = AsyncMock(side_effect=RuntimeError("always fails"))
    decorated = with_retry(max_attempts=3, base_delay=0)(mock_fn)
    with pytest.raises(RuntimeError, match="always fails"):
        await decorated()
    assert mock_fn.call_count == 3


# ── Exception filtering ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_non_retryable_exception_propagates_immediately():
    """Exceptions not in the retry list should NOT be retried."""
    mock_fn = AsyncMock(side_effect=ValueError("bad input"))
    decorated = with_retry(
        max_attempts=3, base_delay=0, exceptions=(RuntimeError,)
    )(mock_fn)
    with pytest.raises(ValueError):
        await decorated()
    assert mock_fn.call_count == 1  # no retries


# ── Max attempts = 1 (no retry) ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_max_attempts_one_means_no_retry():
    mock_fn = AsyncMock(side_effect=RuntimeError("fail"))
    decorated = with_retry(max_attempts=1, base_delay=0)(mock_fn)
    with pytest.raises(RuntimeError):
        await decorated()
    assert mock_fn.call_count == 1


# ── Preserves function metadata ───────────────────────────────────────────────

def test_functools_wraps_preserves_name():
    async def my_function():
        pass
    decorated = with_retry()(my_function)
    assert decorated.__name__ == "my_function"
