# Uniflo — Partner B Detailed Phase 3 Plan (`uniflo-api`)

> Scoped strictly to Phase 3 work in `uniflo-api`. All decisions and constraints referenced here derive from `docs/architecture-designs.md`, `docs/build-action-plan.md`, and `docs/git-github-workflow.md`. This doc lives in `uniflo-web/docs/phase-3/` as the shared coordination artefact — the actual code lands in `uniflo-api`. Per-task write-ups go under `uniflo-api/docs/phase-3/` following the same pattern Partner A uses in `uniflo-web/docs/phase-N/`.

---

## Phase 3 Goal

A real student can apply to at least three SA universities through Uniflo and have those applications actually submitted to the live university portals — without the team touching a browser. Playwright runs the submissions invisibly on the backend, Claude maps the student's profile to each university's form fields and rates its own confidence, and the application status moves from `pending` → `processing` → `submitted` (or `failed`) as the real adapter runs. This is the MVP.

**Duration:** Weeks 9–14
**Reference tag:** `[PHASE-3]`

---

## Before You Write a Single Line of Code

**Do this with Partner A first. Do not skip it.**

Phase 3 introduces real automation and real AI. The contract you lock now governs every adapter, every confidence score, and every status update Partner A renders on the dashboard. Get it wrong and both partners rewrite for two weeks.

### 1. Manual portal research — joint task

Before any code, both partners sit down and **manually complete a full application on each target university portal**. This is non-negotiable per the build plan. No automation lands until the research artefact exists.

For each target portal (start with UCT, Wits, UJ and UP):

- Walk the portal end-to-end with a test account. Take screenshots of every page.
- Document each step in a shared doc — page URL, form field labels, field types (text/select/file/checkbox), required vs optional, validation rules, error messages, post-submit confirmation page.
- Map every portal field to the corresponding `student_profiles` / `academic_records` / `documents` field. Flag fields that have no Uniflo equivalent — these are the gaps that drive Claude's confidence scores down.
- Note the file upload sizes, accepted formats, and the file naming the portal expects.
- Note whether the portal uses captcha, OTP, or any anti-automation measure. If it does, flag it as a blocker and surface it before week 10.
- Capture the post-submit confirmation page exactly — URL, DOM markers, text that proves "submitted". This is what `verify_submission()` keys off and what the screenshot proof captures.

The artefact lives at `uniflo-api/docs/phase-3/portal-research/<university-slug>.md`. One file per portal. Both partners review and sign off in PR before adapter work starts.

### 2. Lock the API surface with Partner A

Partner A's Phase 3 work (`docs/phase-3/partner-a-phase-3-plan.md`) depends on shape decisions you own:

- **Confidence scores per field on `POST /applications`'s response (or a follow-up `GET /applications/{id}/field-mappings`).** Decide which. Partner A renders flagged-low-confidence fields on the review screen and needs the shape locked before Task 2 of their plan.
- **Screenshot proof exposure.** `application_jobs.screenshot_url` is already in schema. Decide whether `GET /applications/{id}` includes the latest job's `screenshot_url` directly or whether Partner A reads it from `latest_job.screenshot_url`. Partner A assumes the latter (their Task 6 already guards for the field's absence in Phase 2).
- **Retry endpoint shape.** Phase 2 left a Partner-A placeholder for "Retry" on failed applications. Lock it now: most likely `POST /applications/{id}/retry` returning `202 Accepted` and the refreshed application row. Confirm idempotency semantics — retrying a `submitted` application is a no-op, retrying a `processing` one is a 409.
- **Failure taxonomy.** What does `application_jobs.last_error` actually contain? A free-text string, a structured `{ code, message, retryable }` object, or a code that Partner A maps to friendly copy? Pick one and document it. Partner A needs this for the "Failed" detail page.
- **Portal-broken state.** When portal health monitoring flags an adapter as down, what does the student see? Either (a) `POST /applications` rejects with a `503` and a code Partner A renders as "Applications to X are temporarily unavailable", or (b) the application is accepted but the job stays in `pending` with a special status. Option (a) is simpler. Pick it unless there's a reason not to.

Both partners sign off in a PR to the OpenAPI spec before Task 2 below starts.

### 3. Test accounts and credentials hygiene

Phase 3 is the first time the system handles real third-party credentials (the test accounts on each portal). Treat them like production secrets from day one:

- Test-account credentials live in the secrets manager (Bitwarden), not in `.env.example` or any committed file
- The adapters read credentials from environment variables loaded into the Render/Railway runtime, never from a config file in the repo
- One test account per portal per developer. Do not share a single account across the team — concurrent automation runs will collide
- Document the test account lifecycle: who created it, when it expires, what student data it uses (synthetic — never real PII)

### 4. AI provider, cost guardrails, and data hygiene

The AI layer uses **Google Gemini 2.5 Flash** as the default model — it's ~6× cheaper than Claude Sonnet for this task (~$0.006 vs ~$0.038 per application), the free tier covers dev iteration at zero cost, and structured-output reliability on a fixed-schema field-mapping task is good enough for MVP. The `ai/client.py` wrapper (Task 3) is built provider-agnostic from day one — swapping to Sonnet, GPT-4.1 Mini, or anything else is a config change, not a rewrite.

Before week 11 (Task 3 below):

- Create a Google AI Studio account and provision a `GEMINI_API_KEY` for dev (free tier — ~10 RPM, ~250 requests/day is plenty for hand-testing). A paid key for CI integration tests and production lands later in Task 3
- Decide the default model. Gemini 2.5 Flash for both mapping and confidence scoring. Flash-Lite is a stretch option for confidence scoring only (faster + cheaper) if Flash's per-call cost matters at production scale — unlikely at MVP
- Log every AI call's input/output tokens + provider + model to a debug table or Sentry breadcrumb during development — surprise bills hit hardest the first time

**Data hygiene — non-negotiable two-rule policy:**

1. **Synthetic data fixtures only in dev and CI.** Build a `tests/fixtures/synthetic_students.py` carrying hardcoded fake profiles, fake academic records, fake document metadata. Never call the AI layer in dev with a real student's PII pulled from the database. Code review enforces this — there's no lint rule that catches it
2. **Move off the Gemini free tier before any real student data flows through.** Google's free tier trains on inputs by default; the paid tier opts out. Real student PII (ID numbers, addresses, marks) reaching the free tier is a POPIA leak — see `docs/architecture-designs.md` section 13. The cutover happens at beta launch (Phase 4) at the latest. Earlier if any production-bound endpoint can reach the AI layer

---

## How to Work Through This Plan

Same workflow rules as Partner A — see `docs/git-github-workflow.md`:

```bash
git fetch origin
git checkout main && git pull --ff-only origin main
git checkout -b feature/<task-branch-name>

# When done — open a PR to main, CI green, Squash and Merge
```

CI must pass (Ruff + Black + Pytest) before any PR merges.

At the end of each task branch, drop a write-up in `uniflo-api/docs/phase-3/` as `task-<n>-<slug>.md` covering what was built, design decisions, deviations from this plan, and how to verify. Mirror Partner A's `docs/phase-1/` and `docs/phase-2/` pattern.

**One adapter per branch.** Adapters are independent. Do not bundle two universities into one PR — when one breaks during review, the other gets held up.

---

## Task 1 — Portal research artefact
**Branch:** `feature/portal-research` (docs-only, no code)

Walk every target portal end-to-end, document everything, get sign-off before any automation lands.

- [x] Create `uniflo-api/docs/phase-3/portal-research/README.md` — index page listing every target portal with a status pill (researched / in progress / blocked)
- [x] Walk UCT's portal with a test account. Document at `uniflo-api/docs/phase-3/portal-research/uct.md` **(draft)**:
  - [~] Every page URL, in order — landing URL captured; per-step URLs `_TBD_`
  - [~] Every form field — label, DOM selector (best effort), type, required/optional, validation — fields + types captured; **selectors all `_TBD_`** (no live access yet)
  - [x] Field → Uniflo profile mapping — conceptual; not yet cross-checked against `student_profiles`/`academic_records` columns
  - [~] File uploads — fields named; accepted types/size limits/naming `_TBD_`
  - [x] Anti-automation measures (captcha, OTP, JS challenges)
  - [ ] Submission confirmation URL + DOM markers — `_TBD_` (needed for `verify_submission()`)
  - [ ] Screenshots — currently linked to Notion (presigned, expiring); **not yet exported** to a `screenshots/` subfolder
- [x] Repeat for Wits at `wits.md` **(draft, same TBDs)**
- [ ] Repeat for Stellenbosch at `stellenbosch.md` — **deferred** (Notion research exists; not yet written up)
- [x] (Stretch) Repeat for UJ and UP — `uj.md`, `up.md` **(draft)** — done in place of Stellenbosch (matches the UCT/Wits/UJ/UP target list in the "Before You Write a Single Line of Code" section)
- [ ] Sign-off PR — both partners review every research doc before Task 2 starts

> **Progress (2026-06-03):** Four drafts on `feature/portal-research` (commit `62a614f`), reformatted from dictated walkthroughs + Notion screenshots. Outstanding across all four: DOM selectors, per-page URLs, submission-confirmation markers, file-upload formats/sizes, screenshot export, and a cross-check of the field mappings against the actual model columns. Blocker check done (see below).

**Deliberate non-goals:** No code, no adapter scaffolding, no Claude integration. This task is the contract that the rest of Phase 3 builds against.

**Blocker check:** If any portal uses captcha or hard anti-automation, raise it in the Sunday sync before week 10. Affected portals get dropped from the MVP target list — the build plan only needs three working.
- **Findings:** UCT = email OTP at signup; Wits = 6-char image security code; UP = image security code — all need OCR/inbox access. **UJ = no captcha** → strongest first-adapter candidate (note: the Task 4 example branch assumes Stellenbosch).

**Squash commit:** `docs: phase 3 portal research for UCT, Wits, Stellenbosch`

---

## Task 2 — Adapter base class + automation scaffolding
**Branch:** `feature/adapter-base`

Build the abstract `UniversityAdapter` and the runtime that drives it — no real portal yet. The first concrete adapter (Task 4) inherits from this without rewriting the runtime.

- [ ] Add `playwright` to `pyproject.toml` and pin to a specific version (Playwright changes fast — pinning prevents surprise breakage)
- [ ] Add `playwright install --with-deps chromium` to the post-install / Docker steps. Confirm Render/Railway can run headed Playwright in headless mode within the deployment image
- [ ] Create `automation/` module with this structure:
  ```
  automation/
  ├── __init__.py
  ├── base.py             # UniversityAdapter ABC
  ├── runtime.py          # browser lifecycle, screenshot capture, timeouts
  ├── exceptions.py       # AdapterError, PortalChangedError, AuthFailedError, etc.
  ├── results.py          # SubmissionResult dataclass
  └── adapters/
      └── __init__.py
  ```
- [ ] Define `UniversityAdapter` in `base.py`:
  ```python
  class UniversityAdapter(ABC):
      university_id: ClassVar[UUID]
      slug: ClassVar[str]  # "uct", "wits"

      @abstractmethod
      async def login(self, page: Page, credentials: PortalCredentials) -> None: ...

      @abstractmethod
      async def fill_form(self, page: Page, mapping: FieldMapping) -> None: ...

      @abstractmethod
      async def upload_documents(self, page: Page, documents: list[Document]) -> None: ...

      @abstractmethod
      async def submit(self, page: Page) -> None: ...

      @abstractmethod
      async def verify_submission(self, page: Page) -> SubmissionConfirmation: ...
  ```
- [ ] Build `runtime.py` — the orchestrator that:
  - Spins up a Playwright browser (Chromium, headless, single context per job)
  - Calls the adapter methods in order
  - Captures a screenshot on every method completion (debugging) and one final confirmation screenshot
  - Wraps everything in a timeout (15 min hard cap per application)
  - Catches `AdapterError` subclasses and turns them into structured `JobFailure` records
  - Tears the browser down cleanly even on failure
- [ ] Define a clear taxonomy in `exceptions.py`:
  - `AuthFailedError` — credentials rejected
  - `PortalChangedError` — selector not found / page shape unexpected (the canary for portal drift)
  - `ValidationFailedError` — portal rejected our submission with a field-level error
  - `HumanActionRequiredError` — runtime hit a captcha / OTP / MFA challenge that can't be solved headlessly (see pause-and-resume note below)
  - `UnknownAdapterError` — catch-all for anything we didn't anticipate
- [ ] **Design the runtime for pause-and-resume from day one.** Captcha-gated portals are out of scope for MVP submission, but the runtime should be structured so a future human-in-the-loop handoff is a small lift, not a rewrite. Concretely:
  - Adapter methods can raise `HumanActionRequiredError(reason, resume_token, browser_state)` to pause the run
  - On pause, the runtime serialises the Playwright `BrowserContext` storage state (cookies + localStorage) to a `paused_jobs` table keyed by the `resume_token`, updates `application_jobs.status` to a new `"paused_human_action"` value, and tears down the browser cleanly
  - The runtime exposes a `resume_job(token)` entry point that rehydrates the browser context from storage and continues from the next adapter method
  - For MVP, no adapter actually raises this — captcha-gated portals are cut from the target list (see "Risks and Open Questions" below). The exception class, the storage path, and the resume entry point exist as scaffolding so Phase 5+ can add a human-in-the-loop UI without touching the runtime
- [ ] Write unit tests for the runtime using a `FakeAdapter` that exercises every code path (success, AuthFailed, PortalChanged, HumanActionRequired pause-and-resume cycle, timeout). No real browser in unit tests — fixture out the page object
- [ ] Document the contract in `uniflo-api/docs/phase-3/task-2-adapter-base.md` — including the pause-and-resume design rationale so Phase 5 picks it up cleanly

**Why no concrete adapter yet:** The base class and runtime are the load-bearing API surface for every adapter that follows. Land them in their own PR so the abstract design gets reviewed without the noise of a 1,000-line UCT portal walkthrough.

**Squash commit:** `feat(automation): adapter base class, runtime, and exception taxonomy`

---

## Task 3 — AI integration: field mapping + confidence scoring (Gemini Flash, provider-agnostic)
**Branch:** `feature/ai-mapping`

The AI layer turns "here's the student's profile and here's the university's form" into "here's the value for each field, and here's how sure I am". This is the brain of the automation layer.

Default provider: **Google Gemini 2.5 Flash**. The wrapper is built provider-agnostic so swapping to Claude Sonnet or GPT-4.1 Mini later is a config change.

- [ ] Add `google-generativeai` to `pyproject.toml` as the primary provider SDK
- [ ] Add `anthropic` and `openai` as optional/extras dependencies — the provider-agnostic interface needs adapters for at least one alternative model so "swap in 30 min" is verified, not aspirational. Recommended: ship the Anthropic adapter alongside Gemini in this PR. The OpenAI adapter can wait until needed
- [ ] Create `ai/` module:
  ```
  ai/
  ├── __init__.py
  ├── client.py           # provider-agnostic AI client (the public interface)
  ├── providers/
  │   ├── __init__.py
  │   ├── base.py         # AIProvider ABC — generate_structured() interface
  │   ├── gemini.py       # GeminiProvider (default)
  │   └── anthropic.py    # ClaudeProvider (fallback / parity check)
  ├── prompts.py          # system + user prompt templates (provider-neutral)
  ├── field_mapping.py    # FieldMapping service
  └── schemas.py          # Pydantic models for mapping requests/responses
  ```
- [ ] Build `providers/base.py::AIProvider` — abstract interface every provider implements:
  ```python
  class AIProvider(ABC):
      @abstractmethod
      async def generate_structured(
          self,
          system: str,
          user: str,
          response_schema: type[BaseModel],
          *,
          temperature: float = 0.0,
      ) -> tuple[BaseModel, TokenUsage]: ...
  ```
  Returns the parsed/validated Pydantic model + a `TokenUsage(input, output, cached_input, provider, model)` dataclass for telemetry
- [ ] Build `providers/gemini.py::GeminiProvider`:
  - Reads `GEMINI_API_KEY` from env
  - Default model: `gemini-2.5-flash` (configurable per instance)
  - Uses Gemini's `response_schema` parameter for native structured output — never rely on the model emitting valid JSON freely
  - Retries on 429 / 5xx with exponential backoff (capped at 3 attempts)
  - Reports token usage from the response metadata
  - **Skip context caching for now.** Gemini's caching has a $1/hr storage fee that doesn't amortise at MVP traffic levels. Revisit once production traffic is steady (Phase 5+)
- [ ] Build `providers/anthropic.py::ClaudeProvider`:
  - Reads `ANTHROPIC_API_KEY` from env
  - Default model: `claude-sonnet-4-6` (configurable per instance)
  - Uses Claude's tool-use mode for structured output
  - Enables prompt caching on the system prompt + portal field schema (`cache_control` markers) — different from Gemini, this caching is automatic prefix-matching with no separate storage fee, so it's a free win when it applies
  - Same retry + telemetry shape as `GeminiProvider`
- [ ] Build `client.py::AIClient` — the public interface the rest of the app uses:
  - Provider selection driven by env: `AI_PROVIDER=gemini|anthropic` (default `gemini`)
  - Model override via `AI_MODEL` env (optional)
  - Logs every call's `TokenUsage` to structured logs + a Sentry breadcrumb. Field mappings to a debug `ai_call_log` table during dev (drop the table or move it behind a flag before prod)
  - Calling code (`field_mapping.py`) never imports a provider directly — it goes through `AIClient`
- [ ] Define the prompt (`prompts.py`) — provider-neutral text, no Anthropic/Gemini-specific markup:
  - System prompt explains the role: "You map a student's structured profile to a university's application form fields. For each form field, return the value to submit and a confidence score 0.0–1.0."
  - User prompt carries (a) the student profile JSON, (b) the form schema (extracted from the portal research doc — list of fields with labels, types, options), (c) any portal-specific context
  - Cap the per-field `reasoning` output to ~50 tokens in the prompt — Partner A needs it for UI hover, not a paragraph. Output token bloat is the single biggest cost lever after model selection
- [ ] Define the response schema (`schemas.py`):
  ```python
  class FieldMappingEntry(BaseModel):
      field_id: str           # portal field identifier
      value: str | None       # the value to submit, None if unmapped
      confidence: float       # 0.0–1.0
      reasoning: str          # short explanation (debugging + UI hover) — capped ~50 tokens
      source_profile_field: str | None  # which profile field this came from

  class FieldMappingResponse(BaseModel):
      university_id: UUID
      application_id: UUID
      entries: list[FieldMappingEntry]
      overall_confidence: float
  ```
- [ ] Build `field_mapping.py::map_application_to_portal()` — orchestrator that:
  - Loads the student's profile + academic records + document list
  - Loads the portal field schema (a JSON file per university, generated from the research doc)
  - Calls `AIClient.generate_structured()` — provider-agnostic
  - Validates and persists the `FieldMappingResponse`
- [ ] Decide the persistence model with Partner A — confidence scores need to flow to the review screen. Two options:
  - (a) Store mappings on a new `field_mappings` table keyed by `application_id`. Exposed via a new endpoint Partner A reads from on the review screen.
  - (b) Inline the mappings into `application_jobs` as a JSON column.
  - Recommendation: (a). Mappings are queried separately from job status and grow over time as adapters are re-run
- [ ] **Synthetic data fixtures.** Create `tests/fixtures/synthetic_students.py` with hardcoded fake profiles, fake academic records, fake document metadata. Every AI integration test pulls from here. Real PII never reaches the AI layer in dev or CI — this is the enforcement point for the data hygiene rule in section 4 above
- [ ] Write tests:
  - Unit tests for `field_mapping.py` with the `AIClient` mocked at the interface level (provider-agnostic test setup)
  - Unit tests for each provider with the underlying SDK mocked
  - **One parity integration test** that runs the same synthetic-profile prompt against Gemini Flash + Claude Sonnet and asserts schema adherence on both, plus reasonable confidence-score agreement (≥0.7 Pearson). Gated behind `RUN_LIVE_TESTS=1`. This is the "we can swap providers in 30 min" claim, verified
  - One live integration test against Gemini Flash with a synthetic profile + fixture portal schema. Gated behind `GEMINI_API_KEY` being set. Free-tier key is fine here
- [ ] Document the prompt in `uniflo-api/docs/phase-3/task-3-ai-mapping.md` — include the locked prompt text, an example request/response on Gemini, the matching example on Claude (parity proof), and the provider-swap procedure
- [ ] Update the per-application cost target — track it actively. Default target: **≤$0.02 per application** with Gemini Flash (gives 3× headroom over the modelled $0.006). If it drifts above, output is bloating — investigate before adding more adapters

**Confidence threshold:** Confirm with Partner A. Default: anything below 0.85 is "low confidence" and gets flagged on the review screen. Threshold lives in shared config (`FIELD_CONFIDENCE_THRESHOLD` env) so it can be tuned without a deploy on both repos.

**Why provider-agnostic from day one:** Costs the team ~30 extra minutes of design work on Task 3. Costs ~1 week of unplanned refactoring later if Gemini's pricing changes, free tier disappears, or schema-adherence regression forces a swap. Asymmetric — do it now.

**Squash commit:** `feat(ai): provider-agnostic AI client with Gemini Flash default and Claude parity adapter`

---

## Task 4 — First adapter (simplest portal) + end-to-end integration
**Branch:** `feature/adapter-<simplest-uni>` (e.g. `feature/adapter-stellenbosch`)

Pick the simplest portal from the research artefact. Build the first concrete adapter, wire it into FastAPI BackgroundTasks, and run a real submission end-to-end.

- [ ] Create `automation/adapters/<slug>.py` implementing `UniversityAdapter`:
  - `login()` — navigate to portal login, fill credentials from env, handle MFA if required (stop with `AuthFailedError` if MFA is required and not solvable headlessly)
  - `fill_form()` — page-by-page, field-by-field, using the `FieldMapping` from Task 3. Wrap every selector lookup in a try/except that raises `PortalChangedError` with the selector that broke
  - `upload_documents()` — match document types to portal upload slots (the mapping comes from the research doc)
  - `submit()` — click through the final "submit" button. Handle modal confirmations
  - `verify_submission()` — confirm we landed on the portal's confirmation URL (or that the confirmation DOM markers exist). Return a `SubmissionConfirmation(reference_number, submitted_at, confirmation_url)`
- [ ] Create the portal field schema JSON at `automation/adapters/<slug>.fields.json` from the research doc
- [ ] Wire the adapter into FastAPI BackgroundTasks. Phase 2 left a stub at `applications/services.py::trigger_application` that logs and updates status. Replace it:
  - On `POST /applications`, enqueue the real adapter via `BackgroundTasks.add_task`
  - Update `application_jobs` rows as the runtime progresses (`pending` → `processing` on adapter start, `submitted`/`failed` on completion)
  - Capture the confirmation screenshot via the runtime, upload to Supabase Storage at `application-screenshots/{application_id}/{job_id}.png`, store the public URL on `application_jobs.screenshot_url`
- [ ] Wire the retry endpoint Partner A is waiting on — `POST /applications/{id}/retry`:
  - 202 + refreshed application row on success
  - 409 if the application is already `processing` or `submitted`
  - 404 if the application doesn't exist or doesn't belong to the requesting student
- [ ] Surface portal-broken state on `POST /applications`. Decide with Partner A in coordination Task 0:
  - If portal health monitoring (Task 6) has flagged this adapter as down, reject with `503` + a structured `{ "code": "portal_unavailable", "university": ... }` body
- [ ] Tests:
  - Unit tests for the adapter's helper methods (selector helpers, field mapping helpers) with the Page object mocked
  - **One integration test that runs the adapter against the real portal** with the dev test account, behind a `RUN_LIVE_TESTS=1` env flag. CI does not run live tests by default — they're for manual verification before merging
  - Test the retry endpoint — happy path, 409, 404
- [ ] Manual verification:
  - Submit an application from the Vercel preview as a real test student
  - Confirm the portal's admin interface shows the application as submitted
  - Confirm the screenshot URL on `application_jobs` opens to the actual confirmation page
  - Confirm the student dashboard moves from `pending` → `processing` → `submitted`
- [ ] Document in `uniflo-api/docs/phase-3/task-4-adapter-<slug>.md` — portal quirks, selectors that drift, manual verification steps

**Why simplest first:** The first adapter is also the first time the runtime, the Claude mapping, the BackgroundTasks integration, and the Supabase Storage screenshot upload all run together. Use a portal you understand inside-out so any failure narrows to one moving part, not five.

**Squash commit:** `feat(automation): <university> adapter and end-to-end submission flow`

---

## Task 5 — Remaining adapters (one per branch)
**Branches:** `feature/adapter-<uni>` per university

Repeat Task 4 for the remaining target universities. One branch and one PR per university. The runtime, Claude integration, BackgroundTasks wiring, screenshot capture, and retry are already done — these branches only add the adapter class and the portal field schema JSON.

- [ ] Adapter 2 — `feature/adapter-<uni>`
- [ ] Adapter 3 — `feature/adapter-<uni>`
- [ ] (Stretch) Adapter 4 — `feature/adapter-<uni>`
- [ ] (Stretch) Adapter 5 — `feature/adapter-<uni>`

For each adapter:

- Inherit from `UniversityAdapter`, implement the five methods using the research doc
- Add the field schema JSON
- Write unit tests for the adapter's specific helpers
- Run the live integration test against the test account
- Submit one real application end-to-end via the Vercel preview before merging
- Drop a write-up in `uniflo-api/docs/phase-3/task-5-adapter-<slug>.md`

**Minimum bar:** Three working adapters by end of Phase 3. The build plan calls for 3–5; ship at 3 if portal complexity eats more time than expected — quality over coverage.

**Squash commits:** `feat(automation): <university> adapter` (one per PR)

---

## Task 6 — Portal health monitoring
**Branch:** `feature/portal-health`

Portals change silently. Selectors break. New required fields appear. The team needs to know before students do.

- [ ] Build `automation/health.py::check_adapter(adapter)`:
  - Spins up the adapter against the test account
  - Walks through `login()` and `fill_form()` with a synthetic profile
  - **Stops before `submit()`** — we never want to submit a fake application during a health check
  - Records `success` / `portal_changed` / `auth_failed` / `unknown`
  - Captures a screenshot if the result is non-success
- [ ] Add a scheduled job (FastAPI startup + APScheduler, or a simple `python -m automation.health` invoked by Render/Railway cron):
  - Run once per day at a low-traffic hour (e.g. 03:00 SAST)
  - Run against every active adapter
  - Persist results to a new `adapter_health` table: `id, university_id, run_at, status, failure_reason, screenshot_url`
- [ ] Surface the health state to the application creation flow:
  - `POST /applications` checks the latest `adapter_health` for the university. If the most recent result is non-success and is fewer than 24h old, reject with `503` + `{ "code": "portal_unavailable" }` per the contract locked with Partner A
- [ ] Notify on failure:
  - On every non-success health check, send a Sentry alert (Sentry already wired in Phase 0) tagged `adapter:<slug>`
  - Optionally email the team via Resend — but Sentry alone is enough for MVP
- [ ] Tests:
  - Unit test the health checker with a `FakeAdapter` that returns each result type
  - Test the `POST /applications` rejection path when health is flagged
- [ ] Document in `uniflo-api/docs/phase-3/task-6-portal-health.md`

**Deliberate non-goals:** No admin UI for health status — Sentry alerts are enough. No automatic adapter disabling beyond the 24h rejection window. No retry of the health check on failure — failure is the signal.

**Squash commit:** `feat(automation): portal health monitoring with daily checks`

---

## Task 7 — Hardening, observability, tests, runbook
**Branch:** `feature/phase-3-hardening`

A polish pass at the end of Phase 3, mirroring Partner A's `feature/phase-2-polish` from Phase 2.

- [ ] Sentry tagging: every adapter run reports `university`, `application_id`, `job_id`, and the adapter phase (`login` / `fill_form` / `upload` / `submit` / `verify`) as Sentry tags. Failures group by adapter phase, not by stack trace
- [ ] Structured logs: every adapter step emits a structured log line — `event=adapter_step adapter=uct phase=fill_form duration_ms=4321 status=ok`. Render's log search is meaningful when logs are structured
- [ ] Cost telemetry: every Claude call records input/output tokens to a `ai_call_log` table or a Sentry custom metric. Weekly review of the table is the cost guardrail
- [ ] Concurrency cap: limit BackgroundTasks to a sensible number of concurrent adapter runs (e.g. 3) on Render's free tier — Playwright is memory-hungry. Use an asyncio semaphore
- [ ] Idempotency on `POST /applications`: same `(student_id, university_id, programme, application_year)` posted twice within 60s returns the existing application instead of a duplicate. Protects against double-clicks on the review screen
- [ ] Soft cleanup of orphaned browsers: a scheduled task kills any Playwright browser process older than 30 min
- [ ] Tests sweep: `pytest --cov` ≥ 70% on the `automation/` and `ai/` modules. Adapters specifically — these are the highest-risk code in the product
- [ ] Runbook at `uniflo-api/docs/phase-3/runbook.md`:
  - "Submissions are failing for X university" — diagnostic flow
  - "Claude is returning low confidence on every field" — likely a portal schema drift
  - "BackgroundTasks queue is backed up" — Render restart procedure
  - "A portal has changed its login flow" — adapter update procedure
- [ ] Cross-phase review doc at `uniflo-api/docs/phase-3/phase-3-review.md` — what shipped, open risks, what unblocks Phase 4
- [ ] Confirm `ruff check`, `black --check`, `pytest`, and the deployment build are all green locally

**Squash commit:** `chore(phase-3): hardening, observability, and runbook`

---

## Phase 3 Checkpoint

Before signing Phase 3 off, verify end-to-end on the live dev environment (Vercel preview + Render backend):

- [ ] Sign in as a real test student with a complete Phase 1 profile and Phase 2-eligible documents
- [ ] Browse `/universities`, select three (one per shipped adapter)
- [ ] Fill in programmes + years
- [ ] On the review screen — at least one low-confidence field is flagged (Partner A renders this)
- [ ] Submit. Watch the dashboard:
  - Each application moves `pending` → `processing` → `submitted` (or `failed`) within ~15 min
  - Each submitted application has a screenshot URL pointing to the real portal confirmation
- [ ] Verify in the portal admin interfaces (or with the test-account inbox) that each application is genuinely in the portal — not a false-positive `verify_submission`
- [ ] Force a failure: temporarily break a selector in one adapter, redeploy, submit. Confirm:
  - The job ends in `failed` with a structured `last_error`
  - Partner A's detail page renders the failure with a "Retry" button
  - Retry posts to `POST /applications/{id}/retry` and re-runs the adapter
- [ ] Force portal-unavailable: mark one adapter as failed via the health table, submit. Confirm `POST /applications` returns 503 and Partner A renders the "temporarily unavailable" state
- [ ] Confirm Sentry shows the failure tagged with `university`, `application_id`, `phase`
- [ ] Confirm cost telemetry shows Claude tokens used per application — within budget

All CI checks green: Ruff + Black + Pytest.

---

## Environment Variables for Phase 3

New env vars to add to `uniflo-api/.env.example` and the Render/Railway runtime:

```bash
# AI provider selection (default: gemini)
AI_PROVIDER=gemini              # gemini | anthropic
AI_MODEL=                       # optional override; defaults to provider's default

# Google Gemini (default provider)
GEMINI_API_KEY=                 # free tier OK in dev; paid key required before any real student data flows

# Anthropic Claude (parity / fallback provider)
ANTHROPIC_API_KEY=              # optional — only needed if AI_PROVIDER=anthropic or for the parity integration test

# Per-portal test account credentials — one block per adapter
PORTAL_UCT_USERNAME=
PORTAL_UCT_PASSWORD=
PORTAL_WITS_USERNAME=
PORTAL_WITS_PASSWORD=
PORTAL_STELLENBOSCH_USERNAME=
PORTAL_STELLENBOSCH_PASSWORD=

# Playwright runtime tuning
PLAYWRIGHT_TIMEOUT_MS=900000    # 15 min hard cap per application
PLAYWRIGHT_CONCURRENCY=3        # max concurrent adapter runs

# Confidence threshold for "flag for review" on the frontend
FIELD_CONFIDENCE_THRESHOLD=0.85

# Gate live integration tests behind a flag — CI does not run them by default
RUN_LIVE_TESTS=0
```

Per the ongoing rule from `docs/build-action-plan.md`, every new env var lands in `.env.example` in the same PR that introduces it.

---

## What Is Explicitly Out of Scope for Phase 3

Per `docs/build-action-plan.md`, do not build any of the following:

- Celery + Redis job queue — FastAPI BackgroundTasks is the MVP queue. Celery is post-MVP (Phase 8)
- Essay / motivation letter Claude integration — confidence scoring + field mapping only
- Supabase Realtime status updates — Partner A's dashboard refreshes on load
- Payments (PayFast)
- SMS notifications (Clickatell)
- Admin dashboard for portal health — Sentry alerts are enough for MVP
- Multi-region deployment, autoscaling, AWS migration — Render dev / Railway beta is the deployment plan
- Adapters for TVET colleges or bursary portals — post-MVP

---

## Risks and Open Questions

Tracked here so they aren't lost between sync meetings. Resolve before or during the task they gate.

- **Resolve before Task 1:** Do any target portals require captcha / phone-OTP / 2FA on submission? If yes, those portals get cut from the MVP target list and deferred to Phase 5+. The Task 2 runtime ships with pause-and-resume scaffolding (`HumanActionRequiredError`, serialised browser state, `resume_job(token)` entry point) so a future human-in-the-loop handoff is a small lift — the student gets a deep link, solves the challenge in their own browser, the adapter resumes from where it paused
- **Resolve before Task 2:** Can Render's deployment image run Playwright with Chromium dependencies installed? If not, we either switch to Railway earlier than planned or use a container with Playwright preinstalled (`mcr.microsoft.com/playwright/python`)
- **Resolve before Task 3:** AI provider commitment. Default is Gemini 2.5 Flash on the free tier in dev. Confirm Google AI Studio account is provisioned and the free-tier quota is sufficient for hand-testing (~250 requests/day)
- **Resolve before Task 3:** Persistence model for field mappings — separate `field_mappings` table (recommended) or JSON on `application_jobs`. Partner A's review screen design depends on this
- **Resolve before Phase 4 beta:** Cutover from Gemini free tier to paid tier. Free tier trains on inputs; real student PII is a POPIA leak. Hard line at the moment any production code path can reach the AI layer with real data
- **Resolve before Task 4:** Failure taxonomy on `application_jobs.last_error` — free text vs structured `{ code, message, retryable }`. Partner A maps this to user-facing copy
- **Resolve before Task 4:** Retry endpoint shape and idempotency rules. Partner A has a placeholder waiting from Phase 2
- **Resolve before Task 6:** Portal-broken state UX — 503 on `POST /applications` vs special "blocked" status on the application row. The plan recommends 503
- **Ongoing risk:** Portal changes during Phase 3 development. The research artefacts age the moment they're written. Re-walk every portal once before Task 5 starts to catch drift early
- **Ongoing risk:** AI cost drift. The Gemini Flash setup targets ≤$0.02 per application (3× headroom over the modelled $0.006). Output token bloat is the primary driver — verbose `reasoning` fields balloon cost fast. Confirm per-application cost in the Google AI Studio dashboard during Task 3 verification and add a regression check before Task 5
- **Ongoing risk:** Gemini free tier rate limits (~10 RPM, ~250 requests/day). Plenty for hand-testing, painful for CI. Live integration tests are gated behind `RUN_LIVE_TESTS=1` for exactly this reason. CI runs the mocked unit tests on every push and the live parity test only on a manual trigger or pre-merge
