"""The mapping orchestrator: profile + portal form schema → FieldMappingResponse,
plus persistence into the `field_mappings` table (Partner-A's review screen).
"""

from typing import Any, Iterable, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.ai.client import AIClient
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.schemas import AIMappingOutput, FieldMappingResponse, PortalFormSchema
from app.config import settings
from app.models.field_mapping import FieldMappingRecord


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


def persist_field_mapping(
    session: Session,
    response: FieldMappingResponse,
    *,
    threshold: Optional[float] = None,
) -> FieldMappingRecord:
    """Upsert the mapping for an application into `field_mappings` (one current
    row per application). Stores the confidence threshold in force so the review
    screen knows which entries were flagged. Caller commits."""
    if threshold is None:
        threshold = settings.FIELD_CONFIDENCE_THRESHOLD
    record = session.exec(
        select(FieldMappingRecord).where(
            FieldMappingRecord.application_id == response.application_id
        )
    ).first()
    entries = [e.model_dump(mode="json") for e in response.entries]
    if record is None:
        record = FieldMappingRecord(
            application_id=response.application_id,
            university_id=response.university_id,
            entries=entries,
            overall_confidence=response.overall_confidence,
            confidence_threshold=threshold,
        )
    else:
        record.university_id = response.university_id
        record.entries = entries
        record.overall_confidence = response.overall_confidence
        record.confidence_threshold = threshold
    session.add(record)
    return record
