"""The mapping orchestrator: profile + portal form schema → FieldMappingResponse.

Persistence is deferred: the plan's `field_mappings` table is a Partner-A
decision (their review screen reads it) and a production migration, so this
returns the validated response and leaves storage to a later wiring step (Task 4).
"""

from typing import Any, Iterable, Optional
from uuid import UUID

from app.ai.client import AIClient
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.schemas import AIMappingOutput, FieldMappingResponse, PortalFormSchema


def _as_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return dict(obj)


def build_profile_payload(
    profile: Any,
    academic_records: Optional[Iterable[Any]] = None,
    documents: Optional[Iterable[Any]] = None,
) -> dict:
    """Flatten profile + academic records + document list into the JSON the
    prompt carries. Accepts model instances or plain dicts."""
    payload: dict = {"profile": _as_dict(profile)}
    if academic_records is not None:
        payload["academic_records"] = [_as_dict(r) for r in academic_records]
    if documents is not None:
        payload["documents"] = [_as_dict(d) for d in documents]
    return payload


async def map_application_to_portal(
    *,
    application_id: UUID,
    profile: dict,
    form: PortalFormSchema,
    client: AIClient,
    extra_context: str = "",
) -> FieldMappingResponse:
    """Map an already-loaded profile payload onto a portal's form schema.

    `profile` is the dict from `build_profile_payload`. Loading it from the DB
    is wired in Task 4; this keeps the AI step pure and testable.
    """
    user = build_user_prompt(profile, form, extra_context=extra_context)
    output, _usage = await client.generate_structured(
        SYSTEM_PROMPT, user, AIMappingOutput, temperature=0.0
    )
    return FieldMappingResponse(
        university_id=form.university_id,
        application_id=application_id,
        entries=output.entries,
        overall_confidence=output.overall_confidence,
    )
