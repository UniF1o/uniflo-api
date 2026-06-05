from uuid import uuid4

from app.ai.field_mapping import build_profile_payload, map_application_to_portal
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.providers.base import TokenUsage
from app.ai.schemas import AIMappingOutput, FieldMappingEntry, FieldMappingResponse
from tests.fixtures.synthetic_students import (
    SYNTHETIC_ACADEMIC_RECORDS,
    SYNTHETIC_DOCUMENTS,
    SYNTHETIC_FORM,
    SYNTHETIC_PROFILE,
)


class FakeAIClient:
    """Stands in for AIClient at the interface level (provider-agnostic test)."""

    def __init__(self, output):
        self._output = output
        self.calls = []

    async def generate_structured(
        self, system, user, response_schema, *, temperature=0.0
    ):
        self.calls.append((system, user, response_schema, temperature))
        return self._output, TokenUsage(
            input=100, output=40, provider="fake", model="fake"
        )


def _canned_output():
    return AIMappingOutput(
        entries=[
            FieldMappingEntry(
                field_id="surname",
                value="Mokoena",
                confidence=0.99,
                reasoning="from last_name",
                source_profile_field="last_name",
            ),
            FieldMappingEntry(
                field_id="home_language",
                value="NORTHERN SOTHO",
                confidence=0.7,
                reasoning="Sepedi maps to Northern Sotho",
                source_profile_field="home_language",
            ),
            FieldMappingEntry(
                field_id="postal_code",
                value="0152",
                confidence=0.6,
                reasoning="needs LOV lookup",
                source_profile_field="postal_code",
            ),
        ],
        overall_confidence=0.8,
    )


async def test_map_application_builds_response():
    app_id = uuid4()
    client = FakeAIClient(_canned_output())
    payload = build_profile_payload(
        SYNTHETIC_PROFILE, SYNTHETIC_ACADEMIC_RECORDS, SYNTHETIC_DOCUMENTS
    )

    resp = await map_application_to_portal(
        application_id=app_id, profile=payload, form=SYNTHETIC_FORM, client=client
    )

    assert isinstance(resp, FieldMappingResponse)
    assert resp.application_id == app_id
    assert resp.university_id == SYNTHETIC_FORM.university_id
    assert {e.field_id for e in resp.entries} == {
        "surname",
        "home_language",
        "postal_code",
    }
    assert resp.overall_confidence == 0.8

    system, user, schema, temp = client.calls[0]
    assert system == SYSTEM_PROMPT
    assert schema is AIMappingOutput
    assert temp == 0.0
    # the user prompt carried the form fields (id + options)
    assert "surname" in user
    assert "NORTHERN SOTHO" in user


def test_low_confidence_filter_uses_threshold():
    resp = FieldMappingResponse(
        university_id=uuid4(),
        application_id=uuid4(),
        entries=_canned_output().entries,
        overall_confidence=0.8,
    )
    flagged = {e.field_id for e in resp.low_confidence(0.85)}
    # 0.7 and 0.6 are below 0.85; surname (0.99) is not
    assert flagged == {"home_language", "postal_code"}


def test_build_profile_payload_flattens():
    payload = build_profile_payload(
        SYNTHETIC_PROFILE, SYNTHETIC_ACADEMIC_RECORDS, SYNTHETIC_DOCUMENTS
    )
    assert payload["profile"]["first_name"] == "Thabo"
    assert payload["academic_records"][0]["subjects"][0]["name"] == "Mathematics"
    assert payload["documents"][0]["type"] == "ID_COPY"


def test_build_user_prompt_lists_every_field():
    user = build_user_prompt({"profile": SYNTHETIC_PROFILE}, SYNTHETIC_FORM)
    for f in SYNTHETIC_FORM.fields:
        assert f.field_id in user
    assert "uj" in user
