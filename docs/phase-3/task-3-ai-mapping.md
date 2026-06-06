# Task 3 — AI field mapping + confidence scoring

The "brain": turns *a student's profile + a university's form schema* into *a
value + confidence for each field*. Provider-agnostic — default **Gemini 2.5
Flash**, with a **Claude Sonnet** parity adapter, swappable by config.

Lives in **`app/ai/`**:

```
app/ai/
├── client.py          # AIClient — the only thing calling code touches
├── field_mapping.py   # map_application_to_portal() orchestrator
├── prompts.py         # provider-neutral system + user prompt
├── schemas.py         # PortalFormSchema / FieldMappingEntry / FieldMappingResponse
└── providers/
    ├── base.py        # AIProvider ABC + TokenUsage
    ├── gemini.py      # GeminiProvider (default) — native response_schema
    ├── anthropic.py   # ClaudeProvider (parity) — tool-use + prompt caching
    └── _retry.py      # 429/5xx exponential backoff
```

## Flow

`map_application_to_portal(application_id, profile, form, client)`:
1. `build_user_prompt(profile, form)` → the user message (profile JSON + every form field).
2. `client.generate_structured(SYSTEM_PROMPT, user, AIMappingOutput)` → the model returns the structured mapping via its **native** structured-output mode (never free-form JSON).
3. Wrap into a `FieldMappingResponse` (adds the ids we own) and return it.

`FieldMappingResponse.low_confidence(threshold)` returns the entries the
frontend flags for review (`FIELD_CONFIDENCE_THRESHOLD`, default 0.85).

## Configuration (env)

| Var | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `gemini` | `gemini` \| `anthropic` |
| `AI_MODEL` | provider default | override the model |
| `GEMINI_API_KEY` | — | required for the Gemini provider |
| `ANTHROPIC_API_KEY` | — | required for the Claude provider |
| `FIELD_CONFIDENCE_THRESHOLD` | `0.85` | below this → flagged for review |

Provider default models: Gemini `gemini-2.5-flash`, Claude `claude-sonnet-4-6`.

## Locked system prompt

```
You map a South African school-leaver's structured profile to a university's
online application form. For each form field, return the value to submit and a
confidence score from 0.0 to 1.0.
Rules:
- Use only data present in the profile; never invent values.
- If no profile data fits a field, set `value` to null with low confidence.
- For select/lov fields, `value` must be one of the field's options — pick the
  closest match and lower the confidence when it isn't exact.
- `confidence` reflects how sure you are the value is both correct and correctly
  formatted for this specific field.
- Keep `reasoning` under ~50 tokens; it's for a reviewer's hover tooltip.
- Set `source_profile_field` to the profile key the value came from.
- `overall_confidence` is your aggregate confidence across all fields.
```

The model must return `AIMappingOutput` — `{ entries: [{ field_id, value,
confidence, reasoning, source_profile_field }], overall_confidence }`.

## Provider-swap procedure (the "30-minute swap", verified)

1. Set `AI_PROVIDER=anthropic` (and optionally `AI_MODEL`).
2. Ensure `ANTHROPIC_API_KEY` is set.
3. Nothing else — `AIClient.from_env()` constructs the right provider; calling
   code (`field_mapping.py`) is unchanged because it only sees `AIClient`.

Both providers implement the same `generate_structured(system, user,
response_schema) -> (model, TokenUsage)` contract: Gemini via `response_schema`,
Claude via tool-use. `TokenUsage` is logged + dropped on a Sentry breadcrumb on
every call for cost telemetry.

## Cost target
**≤ $0.02 per application** with Gemini Flash (3× headroom over the modelled
$0.006). Output-token bloat is the main driver — the `reasoning` cap (~50
tokens/field) is the guard. Verify in the Google AI Studio dashboard once a live
key is wired (Task 3 live test) and add a regression check before Task 5.

## Testing
- `tests/test_ai_field_mapping.py` — the orchestrator with `AIClient` mocked at the interface (provider-agnostic).
- `tests/test_ai_providers.py` — each provider with its SDK mocked: structured-output parse, token-usage extraction, 5xx retry, missing-key guard.
- `tests/test_ai_client.py` — provider selection from env + delegation.
- `tests/fixtures/synthetic_students.py` — **the only** student data the AI tests touch (data-hygiene rule §4: real PII never reaches the AI layer in dev/CI).

## Not in this task (follow-ups / coordination)
- **Live integration tests** (Gemini real call behind `GEMINI_API_KEY`; Gemini↔Claude parity behind `RUN_LIVE_TESTS=1`) — need keys; gated, not run in CI by default.
- **Persistence** — DONE (Task 4): the `field_mappings` table (migration `a9b8c7d6e5f4`, one row per application) is written by `persist_field_mapping(session, response)` and read by Partner-A via `GET /applications/{id}/field-mappings` (each entry carries `flagged = confidence < confidence_threshold`).
- **Per-university form schema JSON** — generated from each research doc as its adapter lands (Task 4/5). Task 3 ships only the `PortalFormSchema` shape + a synthetic fixture form.
- **`AI_MODEL` / threshold sign-off** with Partner A (confidence threshold lives in shared config so it tunes without a deploy).
