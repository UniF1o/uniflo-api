import pytest

from app.ai.client import AIClient
from app.ai.providers.base import TokenUsage
from app.ai.schemas import AIMappingOutput


class FakeProvider:
    name = "fake"
    model = "fake-1"

    def __init__(self):
        self.calls = 0

    async def generate_structured(
        self, system, user, response_schema, *, temperature=0.0
    ):
        self.calls += 1
        return (
            response_schema(entries=[], overall_confidence=0.5),
            TokenUsage(provider="fake", model="fake-1"),
        )


async def test_client_delegates_and_returns_usage():
    provider = FakeProvider()
    client = AIClient(provider)

    result, usage = await client.generate_structured("s", "u", AIMappingOutput)

    assert provider.calls == 1
    assert client.provider_name == "fake"
    assert client.model == "fake-1"
    assert usage.provider == "fake"
    assert result.overall_confidence == 0.5


def test_from_env_unknown_provider_raises(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AI_PROVIDER", "bogus")
    with pytest.raises(ValueError):
        AIClient.from_env()


def test_from_env_selects_gemini(monkeypatch):
    import app.ai.providers.gemini as gem
    from app.config import settings

    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "AI_MODEL", None)
    sentinel = object()
    monkeypatch.setattr(gem, "GeminiProvider", lambda **kw: sentinel)

    client = AIClient.from_env()
    assert client._provider is sentinel
