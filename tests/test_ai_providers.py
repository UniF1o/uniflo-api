from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.schemas import AIMappingOutput

_OUTPUT_DICT = {
    "entries": [
        {
            "field_id": "surname",
            "value": "Mokoena",
            "confidence": 0.99,
            "reasoning": "from last_name",
            "source_profile_field": "last_name",
        }
    ],
    "overall_confidence": 0.9,
}


class _RetryableErr(Exception):
    def __init__(self, code):
        super().__init__("transient")
        self.status_code = code


# --- Gemini --------------------------------------------------------------------

async def test_gemini_parses_structured_output_and_usage():
    fake_resp = MagicMock()
    fake_resp.parsed = AIMappingOutput.model_validate(_OUTPUT_DICT)
    fake_resp.usage_metadata = MagicMock(
        prompt_token_count=120, candidates_token_count=30, cached_content_token_count=0
    )

    with patch("app.ai.providers.gemini.genai"), patch(
        "app.ai.providers.gemini.genai_types"
    ):
        from app.ai.providers.gemini import GeminiProvider

        provider = GeminiProvider(api_key="k")
        provider._client.aio.models.generate_content = AsyncMock(return_value=fake_resp)
        result, usage = await provider.generate_structured("sys", "user", AIMappingOutput)

    assert result.entries[0].field_id == "surname"
    assert usage.input == 120
    assert usage.output == 30
    assert usage.provider == "gemini"


async def test_gemini_retries_on_503_then_succeeds():
    fake_resp = MagicMock()
    fake_resp.parsed = AIMappingOutput.model_validate(_OUTPUT_DICT)
    fake_resp.usage_metadata = MagicMock(
        prompt_token_count=1, candidates_token_count=1, cached_content_token_count=0
    )

    with patch("app.ai.providers.gemini.genai"), patch(
        "app.ai.providers.gemini.genai_types"
    ), patch("app.ai.providers._retry.asyncio.sleep", new=AsyncMock()):
        from app.ai.providers.gemini import GeminiProvider

        provider = GeminiProvider(api_key="k")
        call = AsyncMock(side_effect=[_RetryableErr(503), fake_resp])
        provider._client.aio.models.generate_content = call
        result, _usage = await provider.generate_structured("s", "u", AIMappingOutput)

    assert call.await_count == 2
    assert result.overall_confidence == 0.9


def test_gemini_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch("app.ai.providers.gemini.genai"), patch(
        "app.ai.providers.gemini.genai_types"
    ):
        from app.ai.providers.gemini import GeminiProvider

        with pytest.raises(RuntimeError):
            GeminiProvider(api_key=None)


# --- Claude --------------------------------------------------------------------

async def test_claude_parses_tool_use_and_usage():
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = _OUTPUT_DICT
    fake_resp = MagicMock()
    fake_resp.content = [tool_block]
    fake_resp.usage = MagicMock(
        input_tokens=200, output_tokens=50, cache_read_input_tokens=10
    )

    with patch("app.ai.providers.anthropic.anthropic"):
        from app.ai.providers.anthropic import ClaudeProvider

        provider = ClaudeProvider(api_key="k")
        provider._client.messages.create = AsyncMock(return_value=fake_resp)
        result, usage = await provider.generate_structured("sys", "user", AIMappingOutput)

    assert result.entries[0].value == "Mokoena"
    assert usage.input == 200
    assert usage.cached_input == 10
    assert usage.provider == "anthropic"


def test_claude_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("app.ai.providers.anthropic.anthropic"):
        from app.ai.providers.anthropic import ClaudeProvider

        with pytest.raises(RuntimeError):
            ClaudeProvider(api_key=None)
