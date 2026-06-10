"""Unit tests for the captcha-solving capability (`app/automation/captcha.py`)
and the vision plumbing through `AIClient`. No real model calls — a fake client
serves canned `CaptchaReading`s."""

import pytest

from app.ai.client import AIClient
from app.ai.providers.base import TokenUsage
from app.automation.captcha import (
    CaptchaReading,
    VisionCaptchaSolver,
    clean_reading,
    get_captcha_solver,
    valid_reading,
)
from app.automation.exceptions import CaptchaUnsolvedError

PNG = b"\x89PNG fake image bytes"


class FakeVisionClient:
    """Returns the queued readings one per call, recording temperatures."""

    def __init__(self, readings):
        self.readings = list(readings)
        self.calls = []

    async def generate_vision_structured(
        self, system, user, image, image_mime, response_schema, *, temperature=0.0
    ):
        self.calls.append({
            "system": system, "user": user, "image": image,
            "mime": image_mime, "temperature": temperature,
        })
        return self.readings.pop(0), TokenUsage(provider="fake", model="fake-1")


# --- reading hygiene -----------------------------------------------------------------


def test_clean_reading_strips_wrappers_preserves_case():
    assert clean_reading('  "aB3kQz"  ') == "aB3kQz"
    assert clean_reading("'XyZ123'.") == "XyZ123"
    assert clean_reading("a B 3") == "aB3"


def test_valid_reading_rules():
    assert valid_reading("aB3kQz", length=6, charset="A-Za-z0-9")
    assert not valid_reading("aB3kQ", length=6, charset="A-Za-z0-9")   # short
    assert not valid_reading("aB3k!z", length=6, charset="A-Za-z0-9")  # charset
    assert not valid_reading("", length=None, charset="A-Za-z0-9")
    assert valid_reading("9314", length=None, charset="0-9")


# --- solver -------------------------------------------------------------------------


async def test_solver_returns_first_valid_reading():
    client = FakeVisionClient([CaptchaReading(text=" aB3kQz ")])
    solver = VisionCaptchaSolver(client)
    result = await solver.solve(PNG, length=6)
    assert result == "aB3kQz"  # case preserved verbatim
    assert client.calls[0]["temperature"] == 0.0
    assert client.calls[0]["image"] == PNG
    assert "case-sensitive" in client.calls[0]["system"]


async def test_solver_retries_with_escalating_temperature():
    client = FakeVisionClient([
        CaptchaReading(text="bad reading!!"),         # invalid -> retry
        CaptchaReading(text="", legible=False),       # illegible -> retry
        CaptchaReading(text="Xy9Qr2"),                # valid
    ])
    solver = VisionCaptchaSolver(client)
    result = await solver.solve(PNG, length=6)
    assert result == "Xy9Qr2"
    assert [c["temperature"] for c in client.calls] == [0.0, 0.4, 0.8]


async def test_solver_raises_after_exhausting_attempts():
    client = FakeVisionClient([
        CaptchaReading(text="!!", legible=True),
        CaptchaReading(text="", legible=False),
        CaptchaReading(text="toolong1234", legible=True),
    ])
    solver = VisionCaptchaSolver(client)
    with pytest.raises(CaptchaUnsolvedError) as exc:
        await solver.solve(PNG, length=6)
    assert exc.value.retryable is True
    assert exc.value.code == "captcha_unsolved"


async def test_solver_mentions_length_and_charset_in_prompt():
    client = FakeVisionClient([CaptchaReading(text="abc123")])
    solver = VisionCaptchaSolver(client)
    await solver.solve(PNG, length=6, charset="a-z0-9")
    assert "exactly 6 characters" in client.calls[0]["user"]
    assert "[a-z0-9]" in client.calls[0]["user"]


# --- factory ------------------------------------------------------------------------


def test_get_captcha_solver_none_without_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    assert get_captcha_solver() is None


def test_get_captcha_solver_builds_when_configured(monkeypatch):
    import app.ai.client as client_mod
    from app.config import settings

    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    sentinel = object()
    monkeypatch.setattr(
        client_mod.AIClient, "from_env", classmethod(lambda cls: sentinel)
    )
    solver = get_captcha_solver()
    assert isinstance(solver, VisionCaptchaSolver)
    assert solver._client is sentinel


# --- AIClient vision plumbing ----------------------------------------------------------


async def test_client_vision_delegates_and_logs_usage():
    class FakeProvider:
        name = "fake"
        model = "fake-1"

        def __init__(self):
            self.kwargs = None

        async def generate_vision_structured(
            self, system, user, image, image_mime, response_schema, *, temperature=0.0
        ):
            self.kwargs = dict(
                system=system, user=user, image=image, image_mime=image_mime
            )
            return (
                response_schema(text="aB3", legible=True),
                TokenUsage(provider="fake", model="fake-1"),
            )

    provider = FakeProvider()
    client = AIClient(provider)
    result, usage = await client.generate_vision_structured(
        "s", "u", PNG, "image/png", CaptchaReading
    )
    assert result.text == "aB3"
    assert provider.kwargs["image"] == PNG
    assert provider.kwargs["image_mime"] == "image/png"
    assert usage.provider == "fake"
