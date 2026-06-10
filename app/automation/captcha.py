"""Image-captcha solving via the provider-agnostic AI vision layer.

Phase 3 decision (2026-06-03): the captcha portals stay in the MVP, so the
runtime must ship image OCR/vision — Wits has a 6-char security code at temp-ID
creation; UP a **case-sensitive** one on the new-application form.

Division of labour:

- `VisionCaptchaSolver.solve(image)` produces ONE validated reading of one
  image. Internally it retries the *model call* (escalating temperature) when
  the output fails validation or the model reports the image illegible, then
  raises `CaptchaUnsolvedError`.
- The **adapter** owns the portal loop: submit the reading; if the portal
  rejects it, refresh the captcha image and call `solve` again (a wrong-but-
  plausible reading is only detectable portal-side). After its own attempt
  budget the adapter raises — `captcha_unsolved` is retryable, so a fresh run
  gets a fresh captcha.
- `capture_element_image(page, selector)` screenshots the captcha `<img>` to
  feed the solver.

Case is preserved verbatim — UP's check is case-sensitive.
"""

import logging
import re
from typing import Optional, Protocol

from pydantic import BaseModel

from app.automation.exceptions import CaptchaUnsolvedError

logger = logging.getLogger(__name__)

# Temperature escalation per model attempt: deterministic first, then jitter
# the sampling when the first reading didn't validate.
_ATTEMPT_TEMPERATURES = (0.0, 0.4, 0.8)

_SYSTEM_PROMPT = (
    "You read distorted captcha images from South African university "
    "application portals. Transcribe EXACTLY the characters shown, preserving "
    "upper/lower case — the check is case-sensitive. Do not add spaces, "
    "punctuation, or commentary. If the image is genuinely unreadable, say so "
    "via the legible flag instead of guessing."
)


class CaptchaReading(BaseModel):
    """Structured reading: `text` is the verbatim transcription; `legible`
    False means the model judged the image unreadable (-> retry/refresh)."""

    text: str
    legible: bool = True


class CaptchaSolver(Protocol):
    async def solve(
        self,
        image: bytes,
        *,
        image_mime: str = "image/png",
        length: Optional[int] = None,
        charset: str = "A-Za-z0-9",
    ) -> str: ...


def clean_reading(text: str) -> str:
    """Strip the wrappers models sneak in (whitespace, quotes, periods) from
    both ends — captcha charsets are alphanumeric so edge punctuation is never
    part of the answer — while preserving the case of the characters."""
    return text.strip(" \t\r\n'\"`.").replace(" ", "")


def valid_reading(text: str, *, length: Optional[int], charset: str) -> bool:
    if not text:
        return False
    if length is not None and len(text) != length:
        return False
    return re.fullmatch(f"[{charset}]+", text) is not None


class VisionCaptchaSolver:
    """Reads a captcha image with the configured AI provider (Gemini Flash /
    Claude — both vision-capable)."""

    def __init__(self, client, *, max_attempts: int = len(_ATTEMPT_TEMPERATURES)):
        self._client = client
        self._max_attempts = max_attempts

    async def solve(
        self,
        image: bytes,
        *,
        image_mime: str = "image/png",
        length: Optional[int] = None,
        charset: str = "A-Za-z0-9",
    ) -> str:
        expectation = (
            f"The captcha contains exactly {length} characters"
            if length
            else "The captcha contains a short character sequence"
        )
        user = (
            f"{expectation}, drawn from [{charset}]. "
            "Transcribe it exactly, preserving case."
        )
        last_problem = "no attempt made"
        for attempt in range(self._max_attempts):
            temperature = _ATTEMPT_TEMPERATURES[
                min(attempt, len(_ATTEMPT_TEMPERATURES) - 1)
            ]
            reading, _usage = await self._client.generate_vision_structured(
                _SYSTEM_PROMPT, user, image, image_mime, CaptchaReading,
                temperature=temperature,
            )
            if not reading.legible:
                last_problem = "model reports the image is unreadable"
                logger.info("captcha attempt %d: illegible image", attempt + 1)
                continue
            text = clean_reading(reading.text)
            if valid_reading(text, length=length, charset=charset):
                logger.info(
                    "captcha solved on attempt %d (%d chars)", attempt + 1, len(text)
                )
                return text
            last_problem = f"invalid reading {text!r}"
            logger.info("captcha attempt %d: %s", attempt + 1, last_problem)
        raise CaptchaUnsolvedError(
            f"no valid captcha reading after {self._max_attempts} attempts "
            f"({last_problem})"
        )


async def capture_element_image(page, selector: str) -> bytes:
    """Screenshot one element (the captcha <img>) to feed the solver."""
    return await page.locator(selector).screenshot()


def get_captcha_solver() -> Optional[VisionCaptchaSolver]:
    """The configured solver, or None when no AI provider key is set (adapters
    then raise HumanActionRequiredError at the captcha instead)."""
    from app.config import settings

    provider = (settings.AI_PROVIDER or "gemini").lower()
    has_key = (
        settings.GEMINI_API_KEY if provider == "gemini" else settings.ANTHROPIC_API_KEY
    )
    if not has_key:
        logger.warning("captcha solver unavailable — no %s API key set", provider)
        return None
    from app.ai.client import AIClient

    return VisionCaptchaSolver(AIClient.from_env())
