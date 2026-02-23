"""
retries.py — Exponential backoff retry logic for flaky external calls.

Wraps async functions so transient failures (network blips, Notion
rate limits, MCP subprocess hiccups) are retried automatically before
surfacing an error to the caller.

Usage:
    from retries import with_retry

    @with_retry(max_attempts=3, base_delay=1.0)
    async def call_notion():
        ...

    # or inline:
    result = await with_retry()(some_async_fn)(arg1, arg2)
"""

import asyncio
import functools
import random
from typing import Callable, Type

from logger import get_logger

log = get_logger(__name__)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator factory — retries an async function with exponential backoff
    and full jitter on the specified exception types.

    Args:
        max_attempts:  Total number of attempts (1 = no retry).
        base_delay:    Initial wait in seconds before first retry.
        max_delay:     Cap on wait time between retries.
        exceptions:    Tuple of exception types that trigger a retry.
                       All other exceptions propagate immediately.
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)

                except exceptions as exc:
                    last_exc = exc

                    if attempt == max_attempts:
                        log.error(
                            "retry_exhausted",
                            function=fn.__name__,
                            attempts=attempt,
                            error=str(exc),
                        )
                        raise

                    # Full jitter: sleep = random(0, min(cap, base * 2^attempt))
                    ceiling = min(max_delay, base_delay * (2 ** attempt))
                    sleep_for = random.uniform(0, ceiling)

                    log.warning(
                        "retry_attempt",
                        function=fn.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        retry_in_seconds=round(sleep_for, 2),
                        error=str(exc),
                    )

                    await asyncio.sleep(sleep_for)

            raise last_exc  # unreachable but satisfies type checkers

        return wrapper
    return decorator