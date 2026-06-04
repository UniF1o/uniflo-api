"""Provider-neutral prompt text. No Gemini/Claude-specific markup lives here —
the providers wrap this in their own structured-output machinery."""

import json

from app.ai.schemas import PortalFormSchema

SYSTEM_PROMPT = (
    "You map a South African school-leaver's structured profile to a "
    "university's online application form. For each form field, return the "
    "value to submit and a confidence score from 0.0 to 1.0.\n"
    "Rules:\n"
    "- Use only data present in the profile; never invent values.\n"
    "- If no profile data fits a field, set `value` to null with low confidence.\n"
    "- For select/lov fields, `value` must be one of the field's options — pick "
    "the closest match and lower the confidence when it isn't exact.\n"
    "- `confidence` reflects how sure you are the value is both correct and "
    "correctly formatted for this specific field.\n"
    "- Keep `reasoning` under ~50 tokens; it's for a reviewer's hover tooltip.\n"
    "- Set `source_profile_field` to the profile key the value came from.\n"
    "- `overall_confidence` is your aggregate confidence across all fields."
)


def build_user_prompt(
    profile: dict, form: PortalFormSchema, *, extra_context: str = ""
) -> str:
    parts = [
        "STUDENT PROFILE (JSON):",
        json.dumps(profile, ensure_ascii=False, default=str, indent=2),
        "",
        f"UNIVERSITY: {form.slug}",
        "FORM FIELDS (map every one):",
    ]
    for f in form.fields:
        line = (
            f"- field_id={f.field_id} | label={f.label!r} | type={f.type} "
            f"| required={f.required}"
        )
        if f.options:
            line += f" | options={f.options}"
        if f.help_text:
            line += f" | note={f.help_text}"
        parts.append(line)
    if extra_context:
        parts.extend(["", "PORTAL CONTEXT:", extra_context])
    return "\n".join(parts)
