"""Anthropic Claude provider (parity / fallback). Uses tool-use for structured
output and prompt caching on the system prompt (automatic prefix-match, no
storage fee — a free win when the prefix repeats across calls)."""

import logging
import os
from typing import Optional, TypeVar

from pydantic import BaseModel

from app.ai.providers._retry import with_retries
from app.ai.providers.base import AIProvider, TokenUsage

try:  # SDK optional at import time
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "claude-sonnet-4-6"
_TOOL_NAME = "emit_field_mapping"
_MAX_TOKENS = 4096


class ClaudeProvider(AIProvider):
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_attempts: int = 3,
    ):
        if anthropic is None:  # pragma: no cover
            raise RuntimeError("anthropic is not installed")
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.model = model
        self.max_attempts = max_attempts
        self._client = anthropic.AsyncAnthropic(api_key=key)

    async def generate_structured(
        self,
        system: str,
        user: str,
        response_schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> tuple[T, TokenUsage]:
        tool = {
            "name": _TOOL_NAME,
            "description": "Return the structured field mapping.",
            "input_schema": response_schema.model_json_schema(),
        }
        # cache_control on the system block — repeated prefixes are cached for free.
        system_blocks = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]

        async def _call():
            return await self._client.messages.create(
                model=self.model,
                max_tokens=_MAX_TOKENS,
                temperature=temperature,
                system=system_blocks,
                tools=[tool],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
                messages=[{"role": "user", "content": user}],
            )

        resp = await with_retries(
            _call, max_attempts=self.max_attempts, label=f"claude[{self.model}]"
        )
        return self._parse_tool_response(resp, response_schema)

    async def generate_vision_structured(
        self,
        system: str,
        user: str,
        image: bytes,
        image_mime: str,
        response_schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> tuple[T, TokenUsage]:
        import base64

        tool = {
            "name": _TOOL_NAME,
            "description": "Return the structured reading.",
            "input_schema": response_schema.model_json_schema(),
        }
        system_blocks = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_mime,
                    "data": base64.b64encode(image).decode("ascii"),
                },
            },
            {"type": "text", "text": user},
        ]

        async def _call():
            return await self._client.messages.create(
                model=self.model,
                max_tokens=_MAX_TOKENS,
                temperature=temperature,
                system=system_blocks,
                tools=[tool],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
                messages=[{"role": "user", "content": content}],
            )

        resp = await with_retries(
            _call, max_attempts=self.max_attempts,
            label=f"claude-vision[{self.model}]",
        )
        return self._parse_tool_response(resp, response_schema)

    def _parse_tool_response(self, resp, response_schema: type[T]) -> tuple[T, TokenUsage]:
        tool_input = None
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                tool_input = block.input
                break
        if tool_input is None:
            raise ValueError("Claude returned no tool_use block")
        parsed = response_schema.model_validate(tool_input)

        usage = TokenUsage(
            input=getattr(resp.usage, "input_tokens", 0) or 0,
            output=getattr(resp.usage, "output_tokens", 0) or 0,
            cached_input=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
            provider=self.name,
            model=self.model,
        )
        return parsed, usage
