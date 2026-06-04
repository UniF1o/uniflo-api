"""Phase 3 AI field-mapping layer.

Turns "here's the student's profile + here's the university's form" into "here's
the value for each field and how confident I am". Provider-agnostic: the default
is Google Gemini 2.5 Flash, with a Claude parity adapter, swappable by config.

Calling code goes through `AIClient` (`client.py`) — never a provider directly.
`field_mapping.map_application_to_portal()` is the orchestrator.
"""

from app.ai.client import AIClient
from app.ai.field_mapping import map_application_to_portal
from app.ai.schemas import (
    AIMappingOutput,
    FieldMappingEntry,
    FieldMappingResponse,
    PortalField,
    PortalFormSchema,
)

__all__ = [
    "AIClient",
    "map_application_to_portal",
    "PortalField",
    "PortalFormSchema",
    "FieldMappingEntry",
    "FieldMappingResponse",
    "AIMappingOutput",
]
