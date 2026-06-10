"""Google Gemini provider (default). Uses the unified `google-genai` SDK and
Gemini's native `response_schema` structured output. Context caching is skipped
for now (its $1/hr storage fee doesn't amortise at MVP traffic)."""

import logging
import os
from typing import Optional, TypeVar

from pydantic import BaseModel

from app.ai.providers._retry import with_retries
from app.ai.providers.base import AIProvider, TokenUsage

try:  # SDK is optional at import time so the module imports without it
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None
    genai_types = None

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_attempts: int = 3,
    ):
        if genai is None:  # pragma: no cover
            raise RuntimeError("google-genai is not installed")
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.model = model
        self.max_attempts = max_attempts
        self._client = genai.Client(api_key=key)

    async def generate_structured(
        self,
        system: str,
        user: str,
        response_schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> tuple[T, TokenUsage]:
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        async def _call():
            return await self._client.aio.models.generate_content(
                model=self.model, contents=user, config=config
            )

        resp = await with_retries(
            _call, max_attempts=self.max_attempts, label=f"gemini[{self.model}]"
        )

        parsed = getattr(resp, "parsed", None)
        if parsed is None:
            # Fall back to validating the raw JSON text the model returned.
            parsed = response_schema.model_validate_json(resp.text)

        return parsed, self._usage(resp)

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
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        part = genai_types.Part.from_bytes(data=image, mime_type=image_mime)

        async def _call():
            return await self._client.aio.models.generate_content(
                model=self.model, contents=[part, user], config=config
            )

        resp = await with_retries(
            _call, max_attempts=self.max_attempts, label=f"gemini-vision[{self.model}]"
        )
        parsed = getattr(resp, "parsed", None)
        if parsed is None:
            parsed = response_schema.model_validate_json(resp.text)
        return parsed, self._usage(resp)

    def _usage(self, resp) -> TokenUsage:
        meta = getattr(resp, "usage_metadata", None)
        return TokenUsage(
            input=getattr(meta, "prompt_token_count", 0) or 0,
            output=getattr(meta, "candidates_token_count", 0) or 0,
            cached_input=getattr(meta, "cached_content_token_count", 0) or 0,
            provider=self.name,
            model=self.model,
        )
