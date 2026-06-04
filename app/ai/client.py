"""The public AI interface. Calling code uses `AIClient` and never imports a
provider directly, so swapping Gemini↔Claude is a config change. Every call's
token usage is logged + dropped on a Sentry breadcrumb for cost telemetry."""

import logging
from typing import TypeVar

from pydantic import BaseModel

from app.ai.providers.base import AIProvider, TokenUsage
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIClient:
    def __init__(self, provider: AIProvider):
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._provider.model

    @classmethod
    def from_env(cls) -> "AIClient":
        """Build from `AI_PROVIDER` / `AI_MODEL` config (default gemini)."""
        name = (settings.AI_PROVIDER or "gemini").lower()
        model = settings.AI_MODEL
        if name == "gemini":
            from app.ai.providers.gemini import DEFAULT_MODEL, GeminiProvider

            return cls(GeminiProvider(model=model or DEFAULT_MODEL))
        if name == "anthropic":
            from app.ai.providers.anthropic import DEFAULT_MODEL, ClaudeProvider

            return cls(ClaudeProvider(model=model or DEFAULT_MODEL))
        raise ValueError(
            f"unknown AI_PROVIDER {name!r} (expected 'gemini' or 'anthropic')"
        )

    async def generate_structured(
        self,
        system: str,
        user: str,
        response_schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> tuple[T, TokenUsage]:
        result, usage = await self._provider.generate_structured(
            system, user, response_schema, temperature=temperature
        )
        _log_usage(usage)
        return result, usage


def _log_usage(usage: TokenUsage) -> None:
    logger.info(
        "ai_call provider=%s model=%s in=%d out=%d cached=%d",
        usage.provider,
        usage.model,
        usage.input,
        usage.output,
        usage.cached_input,
    )
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category="ai",
            message="ai_call",
            level="info",
            data={
                "provider": usage.provider,
                "model": usage.model,
                "input_tokens": usage.input,
                "output_tokens": usage.output,
                "cached_input_tokens": usage.cached_input,
            },
        )
    except Exception:  # noqa: BLE001 — telemetry must never break a call
        pass
