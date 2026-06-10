"""The provider-agnostic interface.

Every model backend implements `generate_structured`: given a system + user
prompt and a Pydantic response schema, return the parsed/validated model plus a
`TokenUsage` for telemetry. Providers use their *native* structured-output mode
(Gemini `response_schema`, Claude tool-use) — never free-form JSON parsing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class TokenUsage:
    input: int = 0
    output: int = 0
    cached_input: int = 0
    provider: str = ""
    model: str = ""


class AIProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate_structured(
        self,
        system: str,
        user: str,
        response_schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> tuple[T, TokenUsage]: ...

    @abstractmethod
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
        """`generate_structured` with one inline image (captcha reading etc.).
        Both current backends are vision-capable (Gemini Flash, Claude)."""
        ...
