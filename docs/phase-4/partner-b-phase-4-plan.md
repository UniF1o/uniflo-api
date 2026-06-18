# UniFlo — Partner B Detailed Phase 4 Plan (`uniflo-api`)

> Scoped strictly to Phase 4 backend work in `uniflo-api`: the **course
> recommendation engine** that tells a student which university programmes they
> qualify for. All decisions and constraints referenced here derive from
> `docs/architecture-designs.md`, `docs/build-action-plan.md`,
> `docs/git-github-workflow.md`, and the Phase 3 portal research under
> `docs/phase-3/portal-research/`. Per-task write-ups go under
> `uniflo-api/docs/phase-4/` following the Phase 3 pattern. The matching frontend
> plan is `uniflo-web/docs/phase-4/partner-a-phase-4-plan.md`.

---

## Orientation for a fresh session (read these first)

Written so an agent starting cold (repo access, no chat history) can execute it.
Before coding, read:
- **`uniflo-api/CLAUDE.md`** — stack (FastAPI + SQLModel + Alembic, Python 3.12,
  venv `.venv/`), exact commands, the service-layer pattern, and the ⚠️ **`.env` =
  PRODUCTION DB** warning + current migration head.
- **`app/api/academic_records/schemas.py`** (`SubjectIn`: `name`, `mark`,
  `nsc_level`) and **`service.py`** — the marks shape the matcher consumes and how
  records are fetched.
- **`app/api/universities/`** (public read endpoint) and **`app/api/profiles/`**
  (authenticated; profile resolved from `request.state.user["sub"]`) — the
  `router`/`service`/`schemas` trio to mimic.
- **`scripts/seed_universities.py`** (seed pattern; UP already present),
  **`app/models/__init__.py`** (register new models), a recent
  **`alembic/versions/*`** migration, **`app/main.py`** (router registration), and
  **`tests/conftest.py`** + a `tests/test_*_endpoints.py` (TestClient + mocked
  service + patched-JWT pattern).
- **`docs/phase-3/portal-research/up.md`** — UP's APS examples, programme codes, and
  faculties (the data to transcribe).

Commands (see CLAUDE.md): `pytest -v`, `ruff check .`, `black --check .`. Run
migrations via the Alembic **Python API** (`command.upgrade()`), never the `.exe`.

Prerequisites: Tasks 1–3 need nothing external. Task 4 needs the UP prospectus PDF
(owner provides at kickoff). Cross-repo: this repo owns the contract and ships first;
the frontend regenerates types after deploy.

---

## Phase 4 Goal

A student who has captured their NSC subjects and marks (already built — Academic
Records) can open a page and see, **per university, which programmes they qualify
for**, which they are borderline on, and exactly what is missing on the ones they
do not yet meet. The backend owns the admission-requirements data and the matching
logic; the frontend renders the result.

We ship this **one university end-to-end first** — **University of Pretoria (UP)** —
because UP publishes a clean numeric APS table and per-programme subject minimums,
and because UP's own portal already runs a live minimum-admission check
(`(31100, 501)` — see `docs/phase-3/portal-research/up.md`). Our engine
pre-computes that same check, so this work also directly de-risks the Phase 3 UP
adapter: feeding the AI field-mapper programmes the student actually qualifies for
removes the trial-and-error that currently triggers the portal's rejection.

Everything is built **university-scoped** from day one, so adding Wits/UJ/UCT later
is data-entry plus a scoring function, not a re-architecture.

### Foundation note — this table is the shared course catalogue

The `programmes` table built here is not recommendation-only. It is the **shared
course catalogue** that three initiatives read: this recommendation engine
(requirements), the upcoming **structured programme selection** UI (Phase 5 — let
students pick a specific course in a specific faculty instead of typing free text),
and the **live portal walkthroughs** (which reconcile the portal's study-choice
codes against it — see `portal-walkthroughs-plan.md` in the workspace root). So this
plan models faculties and a canonical `(university_id, qualification_code)` key now,
even though Phase 4 itself only needs them for grouping — that is the foundation that
lets Phase 5 extend rather than refactor. Phase 5 (structured selection + applicant-
type inclusivity) is out of scope here; see the out-of-scope list.

### Settled schema decisions (owned here; mirrored in the frontend plan)

Locked so both repos plan to the same shape:
- **`faculties`** is a table (`university_id`, `name`, nullable `close_date`), not a
  string — faculty is a selectable level and can hold a per-faculty deadline.
- **`programmes`** canonical identity is
  **`(university_id, qualification_code, intake_year)`**; `faculty_id` FK; `min_aps`
  column; subject rules in JSONB `requirements`.
- **`universities.scoring_method`** selects the APS function per university.
- **Phase 5 forward (locked now, built later so both repos design for it):**
  `academic_records.record_type` gains `grade_12_final` (completed/final NSC, for
  gap-year / already-have-matric applicants); `applications.programme` and
  `application_choices.programme` each gain a **nullable** `programme_id` FK kept
  alongside the existing string (additive migration, no breakage). Phase 4 does not
  build these — but the catalogue is shaped for them. (Transfers / tertiary records
  are deferred to post-launch — see out-of-scope.)

**Reference tag:** `[PHASE-4]`

---

## Before You Write a Single Line of Code

**Do this with Partner A first. Do not skip it.** The contract you lock now
governs every card Partner A renders on the new `/courses` page.

### 1. Lock the API surface with Partner A

The single new endpoint is the seam between the repos. Agree and sign off on it in
a PR to the OpenAPI spec before Partner A's Task 2. (The owner has pre-approved the
response shape below; the formal spec sign-off still happens at build time.)

- `GET /recommendations?university_id=<uuid>&record_type=<grade_11_final|grade_12_april|grade_12_june>`
  (authenticated). `record_type` optional; default = **best available** record for
  the student (prefer `grade_12_june` > `grade_12_april` > `grade_11_final`).
- Response (the locked shape — see **Appendix A** for the full schema):
  ```json
  {
    "university_id": "uuid",
    "record_type_used": "grade_12_june",
    "aps": 34,
    "aps_max": 42,
    "programmes": [
      {
        "id": "uuid",
        "name": "BEng (Civil Engineering) ENGAGE",
        "faculty": "Engineering, Built Environment and IT",
        "qualification_code": "12136017",
        "min_aps": 33,
        "status": "qualifies",
        "unmet_rules": []
      },
      {
        "id": "uuid",
        "name": "BEng (Civil Engineering)",
        "faculty": "Engineering, Built Environment and IT",
        "qualification_code": "12130017",
        "min_aps": 35,
        "status": "borderline",
        "unmet_rules": [
          { "requirement": "APS 35", "have": "APS 34", "shortfall": "1 point" }
        ]
      },
      {
        "id": "uuid",
        "name": "BSc (Actuarial and Financial Mathematics)",
        "faculty": "Natural and Agricultural Sciences",
        "qualification_code": "02133186",
        "min_aps": 38,
        "status": "not_yet",
        "unmet_rules": [
          { "requirement": "Mathematics 70%", "have": "Mathematics 58%", "shortfall": "12%" },
          { "requirement": "APS 38", "have": "APS 34", "shortfall": "4 points" }
        ]
      }
    ]
  }
  ```
- **Sort order is part of the contract:** `qualifies` first, then `borderline`,
  then `not_yet`; within each group ascending by APS gap (closest first) so the
  most relevant courses surface at the top of each section.
- `status` enum is exactly `"qualifies" | "borderline" | "not_yet"`. Lock these
  strings before Partner A builds the badge component — `Record<Status, …>`
  exhaustiveness on the frontend will flag any later drift after a types regen.
- **No academic record yet:** if the student has no academic record at all, return
  `409` with a structured `{ "code": "no_academic_record" }` so Partner A renders a
  "Add your subjects first" prompt linking to `/academic-records`, rather than an
  empty list that looks like "you qualify for nothing".

Second endpoint — **now required** (it is the course catalogue, not a nice-to-have):
`GET /universities/{id}/programmes` — the plain faculty→programme catalogue (no
matching), grouped by faculty. The recommendation page can use it, and it is the
endpoint the Phase 5 structured-selection picker (uni → faculty → course) will read.
Building it here means Phase 5 adds a UI, not a backend.

### 2. Confirm the pilot university and the data path

- **Pilot = UP — confirmed in prod.** UP is seeded and live in prod `/universities`
  (`uniflo-api` #50) and is already in `scripts/seed_universities.py` on `main`
  (`up.ac.za`, portal `upnet.up.ac.za`, closes 30 June 2026; Vet Science 31 May). No
  university re-seed needed — just grab UP's `id` from `/universities` when seeding
  programmes.
- **The prospectus is transcribed by Claude Code in-session, not by code.** There
  is no extraction script and no AI-API call in the request path or in tooling.
  The 2027 UP undergraduate prospectus PDF is read directly (Read tool, page by
  page) and transcribed into a reviewable `data/programmes/up.json`. Partner B
  (human) reviews that file in the PR diff before it is seeded — admissions data
  that is wrong actively misleads students, so nothing seeds unreviewed.
- **You must supply the UP prospectus PDF** (commit it to
  `uniflo-api/data/prospectus/up-2027.pdf` or hand over a path). Confirm the
  **intake year** (2027 per the Phase 3 research).

### 3. Lock UP's APS rule from the prospectus

UP's APS in `docs/phase-3/portal-research/up.md` is referenced as "APS 33" for
BEng with subject minimums "English 65% / Maths 65% / Physical Sciences 65%", and
an APS of 34 qualifying for `12136017` but not `12130017`. Before Task 2, read the
prospectus and **write down the exact rule**: how many subjects count (best 6),
whether Life Orientation is included/excluded, the percentage→points band, and any
per-faculty bonus. This goes into `scoring.py` as a single documented function with
unit tests. Do not guess it — transcribe it.

### 4. Data hygiene

The matcher reads the signed-in student's own academic record (real PII on the dev
DB). That is fine for the request path. The **extraction/transcription work uses
only the public prospectus** — no student data involved. Unit tests for the engine
use synthetic subject sets (reuse the `tests/fixtures/synthetic_students.py`
pattern from Phase 3), never real records.

---

## How to Work Through This Plan

Same workflow as Phase 3 — see `docs/git-github-workflow.md`:

```bash
git fetch origin
git checkout main && git pull --ff-only origin main
git checkout -b feature/<task-branch-name>
# When done — open a PR to main, CI green (Ruff + Black + Pytest), Squash and Merge
```

⚠️ **`.env` points at the PRODUCTION database** (`uniflo-api/CLAUDE.md`). The
migration and the seed both run against prod. Keep the migration **additive and
reversible**; run it via the Alembic **Python API** (`command.upgrade()`), never
the `.exe` (it fails silently — see the workspace memory note). Never run an
untested downgrade against prod.

At the end of each task branch, drop a write-up in `uniflo-api/docs/phase-4/` as
`task-<n>-<slug>.md` (what was built, decisions, deviations, how to verify),
mirroring the Phase 3 pattern.

---

## Task 1 — `programmes` data model + migration
**Branch:** `feature/programmes-model`

Introduce the catalogue spine — faculties and programmes — plus the per-university
scoring hook. Faculty is a first-class table, not a string column: the user wants
faculty as a selectable level (the Phase 5 picker), and SA faculties carry real
metadata (UP **Veterinary Science closes 31 May while all other programmes close
30 June** — a per-faculty deadline the single `universities.close_date` can't hold).

- [x] New model `app/models/faculty.py` (exported from `app/models/__init__.py`):

  | column | type | notes |
  |---|---|---|
  | `id` | UUID PK | |
  | `university_id` | UUID FK -> `universities.id` | indexed; unique with `name` |
  | `name` | str | e.g. "Engineering, Built Environment and IT" |
  | `close_date` | date, nullable | per-faculty deadline override (e.g. UP Vet Science) |

- [x] New model `app/models/programme.py` (exported from `app/models/__init__.py`):

  | column | type | notes |
  |---|---|---|
  | `id` | UUID PK | |
  | `university_id` | UUID FK -> `universities.id` | indexed |
  | `faculty_id` | UUID FK -> `faculties.id` | indexed |
  | `name` | str | e.g. "BEng (Civil Engineering) ENGAGE" |
  | `qualification_code` | str, nullable | UP programme code (e.g. `12136017`); part of the canonical key |
  | `intake_year` | int | intake cycle this entry is for (e.g. 2027); part of the canonical key |
  | `min_aps` | int, nullable | per-programme APS threshold |
  | `requirements` | JSONB | structured subject rules (below) |
  | `notes` | text, nullable | caveats (e.g. "5-yr ENGAGE stream", NBT, portfolio) |
  | `is_active` | bool, default `False` | only active programmes are matched/returned |
  | `source_page` | int, nullable | provenance — prospectus page the entry came from |
  | `created_at` / `updated_at` | tz-aware datetimes | match existing models (`onupdate`) |

  The canonical identity of a programme is
  **`(university_id, qualification_code, intake_year)`** — the key the seed upserts on
  and the key the live walkthroughs reconcile the
  portal's study-choice codes against. Treat it as the contract between the
  catalogue, the seed, and the automation layer.

- [x] Additive change to `app/models/university.py`: add `scoring_method`
  (str, nullable) — names the APS function to apply (e.g. `"up_aps"`).
- [x] `requirements` JSONB shape — a list of subject rules. `subjects` is a list
  meaning "any one of these satisfies the rule", which cleanly handles language
  alternatives and the Mathematics-vs-Mathematical-Literacy distinction (only list
  the accepted subjects):
  ```json
  {
    "subject_rules": [
      { "subjects": ["Mathematics"], "min_mark": 65, "min_level": 5 },
      { "subjects": ["Physical Sciences"], "min_mark": 65 },
      { "subjects": ["English Home Language", "English First Additional Language"], "min_mark": 65 }
    ]
  }
  ```
  Subject names MUST come from the frozen NSC list
  (`uniflo-web/lib/constants/nsc-subjects.ts`) — the same list the academic-records
  matcher keys off. `min_mark` is a percentage; `min_level` (NSC 1–7) is optional
  and used when the prospectus states a level rather than a percentage.
- [x] One Alembic migration adding the `faculties` and `programmes` tables + the
  `scoring_method` column. Additive, reversible. Apply via `command.upgrade()`.
- [x] No new tests beyond a model-import smoke test; the logic lives in Task 2.

**Squash commit:** `feat: add programmes table and university scoring_method`

---

## Task 2 — Scoring + matching engine (pure, unit-tested)
**Branch:** `feature/recommendation-engine`

The brain of the feature. Keep it a **pure module** — no DB, no network — so it is
exhaustively unit-testable.

- [x] New `app/api/recommendations/scoring.py`:
  - `compute_aps(subjects: list[SubjectIn], method: str) -> int` — implements UP's
    APS exactly as transcribed in coordination Task 3 (default `up_aps`: sum of the
    NSC achievement levels of the best 6 subjects excluding Life Orientation; the
    percentage→level band is documented inline). Derive level from percentage when
    `nsc_level` is absent (`SubjectIn.nsc_level` is optional), using the documented
    band (e.g. 80–100 → 7, 70–79 → 6, …). Per-university methods are dispatched by
    `university.scoring_method`, so other universities' scoring rules are added here
    as named functions without touching the matcher.
  - `evaluate(subjects, aps, programme) -> MatchResult` returning
    `status` (`qualifies` | `borderline` | `not_yet`), and `unmet_rules` — each a
    `{requirement, have, shortfall}` triple with human-readable strings (the
    frontend renders these verbatim, so phrase them for a student:
    "Mathematics 65%", "Mathematics 58%", "7%").
  - **Borderline threshold** (a named constant, documented): the student meets all
    subject rules but APS is within `APS_BORDERLINE_MARGIN` (default 2) of `min_aps`,
    **or** exactly one subject rule is short by `≤ SUBJECT_BORDERLINE_MARGIN`
    (default 5 percentage points). Everything failing harder is `not_yet`;
    everything met is `qualifies`.
- [x] **Subject-matching rules (correctness landmines) — get these exactly right:**
  match by the exact frozen NSC name; **never** treat `Mathematical Literacy` or
  `Technical Mathematics` as `Mathematics`; keep `English Home Language` and `English
  First Additional Language` distinct (a rule lists whichever it accepts); **exclude
  `Life Orientation`** from the best-6 APS (per the UP rule); ignore `Other` custom
  subjects for named requirements and decide whether they count toward APS; handle a
  record with **fewer than 6 subjects** gracefully (compute on what's there, flag
  provisional — don't error).
- [x] Tests (`tests/test_recommendation_scoring.py`) — truth tables, no DB:
  - APS computation: known subject sets -> expected APS (cover the LO-exclusion and
    the best-6 selection; cover percentage-only input with no `nsc_level`).
  - `evaluate`: a programme the student clearly meets (`qualifies`); one missed only
    on APS by 1 (`borderline`); one missed on a subject by 3% (`borderline`); one
    missed on a subject by 12% and APS by 4 (`not_yet`) with both gap strings
    asserted. Use the UP BEng Civil `12136017` vs `12130017` example from the portal
    research as a fixture so the tests mirror reality.
- [x] `ruff check .` + `black --check .` + `pytest -v` green.

**Squash commit:** `feat: add APS scoring and programme-matching engine`

---

## Task 3 — `/recommendations` endpoint
**Branch:** `feature/recommendations-endpoint`

Wire the engine to the data behind the locked contract, following the standard
`router` / `service` / `schemas` layering.

- [x] New `app/api/recommendations/{router,service,schemas}.py`; register the
  router in `app/main.py`.
- [x] `service.py`:
  - Resolve the student profile from `request.state.user["sub"]` (same lookup every
    other authenticated service uses).
  - Load the academic record: the requested `record_type`, else best available
    (`grade_12_june` > `grade_12_april` > `grade_11_final`); `409 no_academic_record`
    if none.
  - Load the university's **active** programmes **for the active intake year**
    (default the current cycle, e.g. 2027; optionally overridable via an `intake_year`
    query param); compute APS once via
    `scoring.compute_aps(subjects, university.scoring_method)`; run
    `scoring.evaluate` over each programme.
  - Sort qualifies -> borderline -> not_yet, then ascending by APS gap.
- [x] `schemas.py` — Pydantic response models exactly matching Appendix A so the
  generated OpenAPI spec is the contract Partner A regenerates from.
- [x] `router.py` — `GET /recommendations`, authenticated, rate-limited like the
  other read endpoints.
- [x] **Catalogue endpoint** `GET /universities/{id}/programmes` (public, no
  matching) — returns the faculty→programme catalogue for the university (active
  intake year by default), grouped by faculty. Serves browsing now and is the Phase 5
  picker's data source. Same service module.
- [x] Tests (`tests/test_recommendations_endpoint.py`) — `TestClient` + mocked
  service per `tests/conftest.py`: happy path (three buckets present, sort order
  asserted), `409` when no record, auth required.

**Squash commit:** `feat: add GET /recommendations endpoint`

---

## Task 4 — UP prospectus -> `data/programmes/up.json` + seed script
**Branch:** `feature/seed-up-programmes`

The data task. **No extraction script, no AI API** — the prospectus is transcribed
in-session by Claude Code reading the PDF, then reviewed by a human and loaded by a
plain seed script.

- [ ] Claude Code reads `data/prospectus/up-2027.pdf` page-range by page-range and
  transcribes each programme into `data/programmes/up.json`:
  ```json
  [
    {
      "qualification_code": "12136017",
      "name": "BEng (Civil Engineering) ENGAGE",
      "faculty": "Engineering, Built Environment and IT",
      "min_aps": 33,
      "requirements": {
        "subject_rules": [
          { "subjects": ["Mathematics"], "min_mark": 65 },
          { "subjects": ["Physical Sciences"], "min_mark": 65 },
          { "subjects": ["English Home Language", "English First Additional Language"], "min_mark": 65 }
        ]
      },
      "notes": "5-year ENGAGE stream",
      "source_page": 412,
      "is_active": true
    }
  ]
  ```
- [ ] **Capture additional requirements as notes.** Any non-academic requirement a
  programme lists (NBT, portfolio, audition, interview) goes in `notes` — shown to the
  student but never gating (the matcher only checks NSC marks).
- [ ] **Start with one faculty** (recommend Engineering, Built Environment and IT —
  it is the worked example in the portal research) to prove the whole path
  data -> seed -> API -> UI before transcribing the rest of UP in follow-up passes.
  Each pass appends to `up.json`.
- [ ] **Human review (required):** Partner B reviews `up.json` in the PR diff,
  spot-checking entries against the prospectus, before merge/seed.
- [ ] `scripts/seed_programmes.py` — mirrors `scripts/seed_universities.py`: plain
  SQLAlchemy load, no AI; resolves UP's `university_id` by name; **upserts each
  distinct `faculty` name into `faculties` and resolves `faculty_id`**; idempotent
  upsert of programmes by `(university_id, qualification_code, intake_year)` (fallback
  `name` + `intake_year`); sets UP's `scoring_method = "up_aps"` and the file's
  `intake_year` (one prospectus = one intake year). The `up.json` keeps `faculty` as a
  plain
  name string — the seed creates/links the faculty row. Run:
  `python scripts/seed_programmes.py`.
- [ ] Apply against prod (`.env` is prod) only after the JSON is reviewed.

**Squash commit:** `feat: seed UP programme admission requirements`

---

## Task 5 — Remaining universities (one per branch)
**Branches:** `feature/programmes-<uni>` per university

Repeat Task 4 (transcribe prospectus -> `data/programmes/<uni>.json` -> human review
-> seed) for the other supported universities. One branch and one PR each; the model,
engine, and endpoint already exist, so each branch is data plus — only if the
university scores differently — a new `scoring_method` function. These are **later
tasks, not out of scope** — UP ships and proves the pipeline first.

Suggested ordering (most APS-like scoring first, bespoke last):

- [ ] **UJ** — APS-based like UP; reuse `up_aps` if the bands match, else add
  `uj_aps`. Research: `docs/phase-3/portal-research/uj.md`.
- [ ] **Wits** — its own composite/APS with programme-specific subject rules; add
  `wits_aps` if the points differ. Research: `docs/phase-3/portal-research/wits.md`.
- [ ] **UCT** — bespoke **Faculty Points Score (FPS/WPS)** with weighted percentages,
  plus NBT; needs a dedicated `uct_fps` function and a decision on how non-academic
  requirements (NBT) are surfaced (see Risks). Do last. Research:
  `docs/phase-3/portal-research/uct.md`.

For each: transcribe faculty-by-faculty, human-review the JSON in the PR, seed, and
verify a `qualifies`/`not_yet` pair by hand against the prospectus. Write up in
`docs/phase-4/task-5-<uni>.md`.

**Minimum bar:** UP shipped and verified end-to-end; the others land as their data is
transcribed. Correct requirements over coverage.

**Squash commit:** `feat: seed <university> programme admission requirements` (one per PR)

---

## Phase 4 Checkpoint (backend)

Before sign-off, verify end-to-end against the live dev backend:

- [ ] Migration applied to prod; `programmes` exists and `universities` has
  `scoring_method`.
- [ ] One UP faculty's programmes seeded and marked active.
- [ ] As the test student (jane.doe.test26@gmail.com — already has a
  `grade_12_june` record), `GET /recommendations?university_id=<UP>` returns the
  three buckets with sensible APS and gap strings. Cross-check one `qualifies` and
  one `not_yet` by hand against the prospectus.
- [ ] `409 no_academic_record` path returns the structured code for a profile with
  no records.
- [ ] **Do not POST /applications** from the test account — that feeds the live
  Phase 3 automation worker against real UP portals.
- [ ] OpenAPI spec regenerated and deployed so Partner A can run `npm run types:api`.
- [ ] **Cross-check against the portal's real gate:** the UP portal runs the live
  admission check itself (`(31100, 501)`; see `docs/phase-3/portal-research/up.md`).
  Validate the engine on the documented known cases (e.g. APS 34 qualifies for
  `12136017` but not `12130017`) so our pre-computation matches the portal's verdict.
- [ ] `ruff`, `black --check`, `pytest` green.

---

## Cross-repo sequencing (per workspace `CLAUDE.md`)

Backend PRs first -> Render deploy -> `command.upgrade()` against prod -> seed
reviewed UP programmes -> Partner A runs `npm run types:api` -> frontend PR.
Reference the sibling PR in each description. No `Co-Authored-By`, no Claude
attribution on commits/PRs.

---

## Environment Variables for Phase 4

None new. The engine reads existing tables; the seed uses the existing
`DATABASE_URL`. The transcription is an in-session Claude Code task, not a runtime
dependency, so there is **no AI key and no AI config** for this feature.

---

## What Is Explicitly Out of Scope for Phase 4

- AI/LLM API calls of any kind in this feature (extraction is done in-session by
  Claude Code reading the PDF; the request path is pure matching).
- (Universities other than UP are **not excluded** — they are later data tasks; see
  Task 5. Each needs its prospectus transcribed and, if its APS differs, a new
  `scoring_method` function.)
- Storing or recomputing APS on `academic_records` — APS is computed on read.
- Multi-record blending, subject-improvement simulators ("if you raise Maths to
  70%…"), or saved/favourited courses — post-MVP.
- Auto-creating applications from a qualifying course — the frontend Apply CTA reuses
  the existing `/applications/new` flow; no new application plumbing here.
- **Structured programme selection (Phase 5):** replacing the free-text
  `applications.programme` / `application_choices.programme` with a `programme_id` FK
  and a uni→faculty→course picker. The catalogue built here is the foundation for it,
  but the FK migration and picker UI are Phase 5.
- **Applicant-type inclusivity (Phase 5):** gap-year / already-have-matric applicants
  via `academic_records.record_type = grade_12_final`, plus de-assuming "current
  learner" across the flow. These applicants still have NSC marks, so the engine works
  unchanged — it's just a new record type. See `portal-walkthroughs-plan.md` for the
  branch mapping.
- **Transfers — deferred to post-launch.** Applicants with tertiary records would need
  a new tertiary record model and case-by-case, university-specific admission the
  NSC-based matcher can't do well. Revisit after launch. (The walkthroughs note the
  branch exists for future awareness; it is not a build target now.)
- **Postgraduate applications — out of scope (not yet).** More complex admission
  logic; revisit once the undergraduate experience (incl. transfers) is complete. The
  walkthroughs do not map postgrad paths.

---

## Risks and Open Questions

- **Resolve at build start (Task 2):** the exact UP APS rule (best-6, Life
  Orientation handling, percentage→points band, bonuses) — transcribed from the
  prospectus the owner provides at Partner B kickoff. Do not infer.
- **Resolve at build start (Task 4):** the UP prospectus PDF (owner provides at
  kickoff) and intake year (2027). UP itself is already confirmed in prod and in the
  seed — no university re-seed needed.
- **Resolve with Partner A:** the `status` enum strings and the `409 no_record`
  shape, before they build the badge and empty states.
- **Data accuracy is the headline risk.** A wrong `min_aps` or subject minimum tells
  a student they (don't) qualify when the opposite is true. Every transcribed entry
  is human-reviewed in the PR diff; start with one faculty and check it hard before
  scaling.
- **Prospectus drift.** Requirements change per intake year; tag each `up.json`
  entry with `source_page` and treat the file as versioned per intake.
- **Intake-year dimension — decided: added now.** `programmes` carries an
  `intake_year` column (part of the canonical key); endpoints default to the active
  cycle (2027) and the seed sets it per prospectus, so future cycles' data coexists
  instead of overwriting — no later migration needed. Remaining nuance: when a new
  cycle opens, decide which year counts as "active" (likely the latest open cycle).
- **Maintenance is recurring, not one-off:** the catalogue + requirements must be
  re-transcribed each intake cycle, and across UP + later universities that is a large
  manual effort. Plan owner time for a per-cycle refresh — it is the real cost centre.
- **Catalogue is the reconciliation point:** the live walkthroughs map the portal's
  study-choice picker and its codes; the prospectus is the source of truth for the
  catalogue. Both must agree on `(university_id, qualification_code)`. If a portal's
  code differs from the prospectus code, store the portal's code separately (a later
  `portal_code` column) rather than overwriting the canonical key. See
  `portal-walkthroughs-plan.md`.
- **Non-academic requirements — settled: notes only, never gating.** NBT scores,
  portfolios, auditions, and interviews aren't NSC marks, so the matcher never gates
  on them — it checks NSC marks only. Students don't even submit NBT scores (UCT
  obtains them from the test body), so we can't and don't score them. During
  transcription, record any such requirement in the programme `notes`; the response
  carries it and the UI shows "Also requires: …" without changing the status.
- **Faculty/programme-level deadlines:** `faculties.close_date` can now differ from
  `universities.close_date` (UP Vet Science). The existing application-deadline
  check reads the university date — when finer-grained deadlines matter, that check
  must prefer the faculty/programme date. Follow-on, not built in Phase 4.
- **Synergy to flag (not a risk):** once seeded, this same data lets the Phase 3 UP
  adapter's AI field-mapper pick only qualifying programmes, avoiding the portal's
  `(31100, 501)` minimum-admission rejection. Coordinate so both features read the
  one `programmes` table.

---

## Appendix A — locked response schema

```python
# app/api/recommendations/schemas.py
from enum import Enum
from pydantic import BaseModel

class MatchStatus(str, Enum):
    QUALIFIES = "qualifies"
    BORDERLINE = "borderline"
    NOT_YET = "not_yet"

class UnmetRule(BaseModel):
    requirement: str   # "Mathematics 65%"  | "APS 35"
    have: str          # "Mathematics 58%"  | "APS 34"
    shortfall: str     # "7%"               | "1 point"

class ProgrammeMatch(BaseModel):
    id: str
    name: str
    faculty: str | None
    qualification_code: str | None
    min_aps: int | None
    status: MatchStatus
    unmet_rules: list[UnmetRule]
    notes: str | None   # additional requirements (NBT, portfolio…), shown not scored

class RecommendationsResponse(BaseModel):
    university_id: str
    intake_year: int
    record_type_used: str
    aps: int
    aps_max: int
    programmes: list[ProgrammeMatch]
```
