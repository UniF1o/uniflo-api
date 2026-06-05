"""Request/response models for the AI field-mapping layer.

`AIMappingOutput` is the exact shape we ask the model to emit (via the
provider's native structured-output mode). `FieldMappingResponse` is what the
orchestrator returns — the model output plus the ids we already know.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PortalField(BaseModel):
    """One field in a university's application form, extracted from the portal
    research doc. The per-university form schema is a list of these."""

    field_id: str  # stable identifier the adapter also keys off
    label: str  # the visible label/role the user sees
    type: str  # text | select | date | checkbox | lov | file | ...
    required: bool = False
    options: Optional[list[str]] = None  # for select/lov fields
    help_text: Optional[str] = None


class PortalFormSchema(BaseModel):
    university_id: UUID
    slug: str
    fields: list[PortalField]


class FieldMappingEntry(BaseModel):
    field_id: str
    value: Optional[str] = None  # the value to submit; None if unmapped
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""  # short — capped ~50 tokens in the prompt
    source_profile_field: Optional[str] = None


class AIMappingOutput(BaseModel):
    """The structured output we require from the model — no ids (we own those)."""

    entries: list[FieldMappingEntry]
    overall_confidence: float = Field(ge=0.0, le=1.0)


class FieldMappingResponse(BaseModel):
    university_id: UUID
    application_id: UUID
    entries: list[FieldMappingEntry]
    overall_confidence: float = Field(ge=0.0, le=1.0)

    def low_confidence(self, threshold: float) -> list[FieldMappingEntry]:
        """Entries the frontend should flag for human review."""
        return [e for e in self.entries if e.confidence < threshold]
