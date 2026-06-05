# Task 2 — Adapter base class + automation runtime

The load-bearing contract every portal adapter is built on. No concrete adapter
yet (that's Task 4); this is the abstract surface + the runtime that drives it.

Lives in **`app/automation/`** (separate from the Phase 2 stub at
`app/api/automation/background.py`, which still simulates jobs until an adapter
replaces it):

```
app/automation/
├── __init__.py        # public exports
├── base.py            # UniversityAdapter ABC + PortalCredentials/DocumentRef/FieldMapping
├── runtime.py         # drive() core + run_job/resume_job browser lifecycle + PauseStore
├── exceptions.py      # AdapterError taxonomy
├── results.py         # SubmissionResult / SubmissionConfirmation / JobFailure / Screenshot
└── adapters/          # concrete adapters (empty until Task 4)
```

## The adapter contract

A `UniversityAdapter` sets two class vars (`university_id`, `slug`) and
implements five async steps the runtime calls **in order** against a live
Playwright `Page`:

1. `login(page, credentials)` — authenticate / begin the application.
2. `fill_form(page, mapping)` — walk the form, entering each value from the `FieldMapping`.
3. `upload_documents(page, documents)` — attach docs (no-op where none are needed, e.g. UJ).
4. `submit(page)` — the final submit (after the student's consent is already recorded).
5. `verify_submission(page)` → `SubmissionConfirmation` — read the success marker.

**Drive mechanism (locked, Phase 3 decision): accessibility-tree primary.**
Adapters target visible roles/labels, not hardcoded CSS. An adapter must never
touch the DB or the runtime — it only acts on the `page` it's handed. Every
selector/label lookup should be wrapped so a miss raises `PortalChangedError`
(the canary for portal drift).

`FieldMapping` is a plain name→value map for now; **Task 3** enriches it with
per-field confidence + a flagged-for-review set, additively, so adapters written
against `.get(name)` keep working.

## The runtime

- **`drive(adapter, page, ...)`** — the testable core. Runs the five steps,
  captures a screenshot after each, applies a hard timeout
  (`DEFAULT_TIMEOUT_S` = 15 min), and converts any `AdapterError` into a
  structured `SubmissionResult`. **It never raises.**
- **`run_job(adapter, ...)`** — production entry: launches a fresh headless
  Chromium context, calls `drive`, tears the browser down cleanly even on
  failure.
- **`resume_job(adapter, token, ...)`** — rehydrates a paused context and
  continues from the next step (see below).

`run_job`/`resume_job` need a real browser, so they're covered by the Task 4
integration, not the unit tests. The unit tests drive everything — including the
resume path — through `drive(..., start_at=…)` with a fake page.

### Outcomes (`SubmissionResult.outcome`)
- `SUBMITTED` — all five steps completed; `confirmation` is set.
- `FAILED` — an `AdapterError` (or anything unexpected, or the timeout) fired; `failure` is set.
- `PAUSED` (`"paused_human_action"`) — a human-action challenge paused the run; `resume_token` is set.

## Exception taxonomy (`exceptions.py`)

Every adapter failure is an `AdapterError` subclass carrying a stable `code` and
a `retryable` hint; the runtime flattens it into a `JobFailure(code, message,
retryable, selector?, field?)`.

| Exception | `code` | retryable | When |
|---|---|---|---|
| `AuthFailedError` | `invalid_credentials` | no | login rejected |
| `PortalChangedError` | `portal_changed` | no | selector/label missing → drift (carries `selector`) |
| `ValidationFailedError` | `form_submit_failed` | no | portal rejected a field (carries `field`) |
| `HumanActionRequiredError` | `human_action_required` | no | captcha/OTP/MFA → pause |
| `UnknownAdapterError` / unexpected | `internal_error` | yes | anything unanticipated |
| (timeout) | `timeout` | yes | exceeded the 15-min cap |

> `portal_changed` and `human_action_required` **extend** the Phase 2
> `JOB_ERROR_CODES` set (`app/api/automation/background.py`). Reconcile/freeze
> the canonical set with Partner A in **Task 4** (the plan's "failure taxonomy"
> open question), since the frontend copy-map keys off it.

## Pause-and-resume (built from day one)

When a step raises `HumanActionRequiredError`, the runtime:
1. captures the browser context's `storage_state()` (cookies + localStorage),
2. saves it to a `PauseStore` against a generated `resume_token`, tagged with the paused step,
3. returns a `PAUSED` result and tears the browser down.

`resume_job(token)` loads the stored state, opens a context seeded with it, and
continues from **the next step** (the plan's "continue from the next adapter
method" — the paused step is assumed completed in the live browser by whoever
handled the challenge).

`PauseStore` is a `Protocol`; Task 2 ships only `InMemoryPauseStore`. A
DB-backed store (the plan's `paused_jobs` table + an `application_jobs` status of
`"paused_human_action"`) is a later lift — the resume entry point already exists
for it to plug into.

**Rationale / MVP note:** captcha/OTP portals are **kept in the MVP** (Phase 3
decision — they solve their challenge inline via OCR + email inbox-read, so they
don't raise `HumanActionRequiredError`). The pause/resume path therefore has no
caller yet; it exists so a future human-in-the-loop handoff (Phase 5+) is a
small lift, not a runtime rewrite.

## Testing

`tests/test_automation_runtime.py` drives a `FakeAdapter` + `FakePage` (no real
browser) across every path: full success, auth/portal-changed/validation/unknown
failures, the 15-min timeout, the pause-and-persist cycle, and resume-from-next-step.
`asyncio_mode = "auto"` (pyproject) lets the async tests run without per-test markers.

## Not in this task (follow-ups)
- **Browser binaries on deploy:** `playwright install --with-deps chromium` must run in the Render/Railway image; confirm the deploy image can run headless Chromium (plan's "resolve before Task 2" ops question). The pip package is pinned (`playwright==1.60.0`); binaries are *not* pulled by pip.
- **Job wiring:** persisting `SubmissionResult` → `application_jobs` (status, `last_error`, screenshot upload to Storage → `screenshot_url`) and replacing the Phase 2 `process_application` stub — Task 4.
- **`FieldMapping` enrichment** (confidence/flags) — Task 3.
- **DB-backed `PauseStore`** + `"paused_human_action"` status — when human-in-the-loop UI lands.
