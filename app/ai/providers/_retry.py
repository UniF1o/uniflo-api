"""Shared retry helper for provider calls — exponential backoff on 429/5xx."""

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_RETRYABLE_CODES = {429, 500, 502, 503, 504}


def is_retryable(exc: Exception) -> bool:
    for attr in ("status_code", "code", "status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int) and val in _RETRYABLE_CODES:
            return True
    return False


async def with_retries(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    label: str = "",
) -> T:
    last: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001 — re-raised below if not retryable
            last = exc
            if attempt < max_attempts and is_retryable(exc):
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "%s retry %d/%d after %.1fs: %s",
                    label,
                    attempt,
                    max_attempts,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                continue
            raise
    assert last is not None  # pragma: no cover
    raise last
