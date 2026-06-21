# UniFlo — Partner B Detailed Phase 5 Plan (`uniflo-api`)

> Scoped strictly to Phase 5 backend work in `uniflo-api`: **structured programme
> selection** (let students pick a specific course in a specific faculty instead of
> typing free text) and **applicant-type inclusivity** (gap-year / already-have-matric
> applicants via `academic_records.record_type = grade_12_final`, and de-assuming
> "current learner" through the apply + automation flow). Both were locked as Phase 5
> forward work in the Phase 4 plans; this plan builds them. All decisions derive from
> `docs/architecture-designs.md`, `docs/build-action-plan.md`,
> `docs/git-github-workflow.md`, the Phase 4 plans, the Phase 3 portal research under
> `docs/phase-3/portal-research/`, and the workspace `portal-walkthroughs-plan.md`.
> Per-task write-ups go under `uniflo-api/docs/phase-5/` following the Phase 3/4
> pattern. The matching frontend plan is
> `uniflo-web/docs/phase-5/partner-a-phase-5-plan.md`.

---

## Phase-track note (read first)

The original `docs/build-action-plan.md` table labels "Phase 4" as *beta hardening*.
The team's **executed** track diverged: Phase 4 shipped the course-recommendation
engine ("Courses you qualify for"). This plan continues the **executed** track —
"Phase 5" here is the structured-selection + inclusivity work every Phase 4 doc
forward-references, not the build-plan's beta-hardening phase. Beta hardening (POPIA,
security audit, load test, paid tiers) still has to happen; it is a separate later
effort and is **out of scope here**. Reconciling the build-plan table to the executed
track is a cheap follow-up the owner can do whenever; it does not block this work.

---

## What landed in Phase 4 (the foundation this builds on)

Phase 4 (`uniflo-api` #50–#61) shipped the catalogue spine and matcher this plan
extends. Confirmed live in prod:

- **`faculties` + `programmes` tables**, canonical key
  `(university_id, qualification_code, intake_year)`; `programmes.requirements` JSONB,
  `min_aps`, `qualification_type`, `duration_years`, `combination` JSONB, `is_active`,
  `source_page`. `universities.scoring_method` selects the APS function.
- **Seeded + active in prod:** UP (120), UJ (177), Wits (56), UCT (29) — all
  faculties, intake_year 2027. Migration head **`c3d2b1a4e5f6`**.
- **`GET /recommendations`** (matcher) and **`GET /universities/{id}/programmes`**
  (the plain faculty→programme catalogue, grouped by faculty, `close_date` per
  faculty) — both live. The catalogue endpoint already exists *specifically* as the
  Phase 5 picker's data source.
- **Portal walkthroughs COMPLETE for all four portals** (UJ, UP, Wits, UCT) — see
  `portal-walkthroughs-plan.md`. Every applicant-type branch (still-in-matric,
  **completed-matric / gap-year**, and the deferred transfer branch) is mapped, with
  field-option sets in `app/automation/adapters/<slug>.fields.json` and branch maps in
  `docs/phase-3/portal-research/<slug>.md`. **This is the precondition that makes
  inclusivity buildable now** — the completed-matric branch is no longer unknown.

Nothing in Phase 4 has to change. Phase 5 is additive on top of it.

---

## Orientation for a fresh session (read these first)

Written so an agent starting cold (repo access, no chat history) can execute it.
Before coding, read:
- **`uniflo-api/CLAUDE.md`** — stack (FastAPI + SQLModel + Alembic, Python 3.12,
  venv `.venv/`), exact commands, the service-layer pattern, and the ⚠️ **`.env` =
  PRODUCTION DB** warning + current migration head (`c3d2b1a4e5f6`).
- **`app/models/application.py`** + **`app/models/application_choice.py`** — where the
  nullable `programme_id` FK lands (Task 1). **`app/models/programme.py`** /
  **`app/models/faculty.py`** — the catalogue it points at.
- **`app/api/applications/{schemas,service,router}.py`** — `ApplicationCreate`
  (validates `programme` free text + `additional_programmes`), `ApplicationRead`,
  `ApplicationChoiceRead`. The seam structured selection extends.
- **`app/api/academic_records/schemas.py`** (`RecordType` enum — add `grade_12_final`)
  and **`service.py`** (best-available record logic also lives in the recommendation
  service).
- **`app/api/recommendations/{service,schemas}.py`** — the best-available ordering
  (`grade_12_june > grade_12_april > grade_11_final`) that must learn `grade_12_final`,
  and the existing catalogue endpoint.
- **`app/automation/adapters/<slug>.py`** + **`<slug>.fields.json`** and
  **`docs/phase-3/portal-research/<slug>.md`** — the adapters and the now-complete
  branch maps the completed-matric automation reads (Tasks 5–6).
- A recent **`alembic/versions/*`** migration, **`app/main.py`** (router registration),
  **`tests/conftest.py`** + a `tests/test_*_endpoints.py` (TestClient + mocked service
  + patched-JWT pattern), and **`tests/fixtures/synthetic_students.py`**.

Commands (see CLAUDE.md): `pytest -v`, `ruff check .`, `black --check .`. Run
migrations via the Alembic **Python API** (`command.upgrade()`), never the `.exe`
(it fails silently — workspace memory note).

⚠️ **`.env` points at the PRODUCTION database.** The one migration in this phase
(Task 1) runs against prod. Keep it additive and reversible; never run an untested
downgrade against prod.

---

## Phase 5 Goal

Two independent tracks. They share no migration and can ship in either order, but
**Track 1 is lower-risk and touches no live portals, so do it first.**

**Track 1 — Structured programme selection.** Today an application carries a free-text
`programme` string. Phase 5 lets the student pick a real catalogue programme; the
application records a nullable `programme_id` FK **alongside** the existing string (the
string stays as the human-readable denormalised name and the back-compat path). The
catalogue endpoint already exists; this track is the FK + the contract that accepts and
returns it. The frontend builds the uni → faculty → course picker on top.

**Track 2 — Applicant-type inclusivity.** Today the data model and the automation
assume the applicant is *currently in Grade 12*. Phase 5 adds the
`grade_12_final` record type (completed / final NSC — gap-year, already-have-matric,
school-leaver from a prior year) and de-assumes "current learner" through the apply
gate and the portal automation. The recommendation **engine is unchanged** — these
applicants still have NSC marks, so matching works on whatever record exists; the work
is the record type, the best-available ordering, the apply-gate relaxation, and the
per-portal completed-matric automation branch (now that the walkthroughs mapped it).

**Reference tag:** `[PHASE-5]`

### Settled decisions carried from Phase 4 (locked — both repos plan to these)

From the Phase 4 plans' "Phase 5 forward" notes:
- **`applications.programme_id` and `application_choices.programme_id`** are **nullable**
  FKs kept *alongside* the existing `programme` string. Additive migration, no breakage:
  old free-text applications keep working with `programme_id = NULL`.
- **`academic_records.record_type` gains `grade_12_final`.** `record_type` is a plain
  `str` column (not a Postgres enum) with a `(student_id, record_type)` unique
  constraint, so a student can hold a `grade_12_final` record alongside the others.
  **No migration is needed** — the change is the Pydantic `RecordType` enum + the
  best-available ordering. (Confirm the column is still a plain string before relying
  on this; it is as of head `c3d2b1a4e5f6`.)
- **Transfers / tertiary records and postgraduate applications stay deferred to
  post-launch** (see out-of-scope). The walkthroughs note the transfer branch exists;
  Phase 5 does not build it.

---

## Before You Write a Single Line of Code

**Do this with Partner A first. Do not skip it.** Track 1 changes the application
contract; Track 2 changes a record-type enum Partner A renders. Both are seams.

### 1. Lock the contract deltas with Partner A (one OpenAPI PR per track)

Sign these off in a PR to the OpenAPI spec before Partner A consumes them.

**Track 1 — `programme_id` on the application contract (Appendix A):**
- `ApplicationCreate` accepts optional `programme_id` (uuid) and optional
  `additional_programme_ids` (list of uuid, same order/cap as `additional_programmes`).
- When `programme_id` is supplied: validate it is an **active** programme **of the
  posted `university_id`**, and **derive the `programme` name from the catalogue** so
  the stored string always matches the chosen id (the id wins; the client-sent name is
  for display only and is overwritten). When only free text is supplied, `programme_id`
  stays `NULL` (back-compat).
- `ApplicationRead.programme_id` and `ApplicationChoiceRead.programme_id` are returned
  (nullable). Partner A's `Record<…>` exhaustiveness will flag enum drift after regen.

**Track 2 — `grade_12_final` record type:**
- `RecordType` enum gains `grade_12_final`. Lock the **best-available preference order**
  with Partner A before they touch labels:
  `grade_12_final > grade_12_june > grade_12_april > grade_11_final` (a completed/final
  NSC is the most authoritative record, so it wins when present).
- Confirm with Partner A which `current_activity` values the apply flow will now permit
  (Track 2, Task 5) so the frontend gate and the server guard agree.

### 2. Source of truth for the completed-matric automation branch

The branch is **already mapped** — do not re-walk the portals. Read each portal's
completed-matric findings before extending its adapter:
- `docs/phase-3/portal-research/<slug>.md` — the branch map (what "Completed Grd 12" /
  gap-year unlocks: exam-number fields, exemption type, "Post School Activity", etc.).
- `app/automation/adapters/<slug>.fields.json` — the captured option sets for those
  branch fields.
- `portal-walkthroughs-plan.md` "Applicant-type branches to walk" per portal — the
  per-portal list of what changes on the completed-matric path.

### 3. Data hygiene

The recommendation/apply paths read the signed-in student's own record (real PII on the
dev DB) — fine for the request path. **Automation tests use synthetic completed-matric
students** (extend `tests/fixtures/synthetic_students.py`), never real records. ⚠️ Per
CLAUDE.md and the workspace rules, **do not POST /applications from the test account
during verification** — that feeds the live automation worker against real portals.

---

## How to Work Through This Plan

Same workflow as Phase 3/4 — see `docs/git-github-workflow.md`:

```bash
git fetch origin
git checkout main && git pull --ff-only origin main
git checkout -b feature/<task-branch-name>
# When done — open a PR to main, CI green (Ruff + Pytest), Squash and Merge
```

⚠️ The one migration (Task 1) runs against **prod**. Additive + reversible; apply via
`command.upgrade()`, never the `.exe`. At the end of each task branch drop a write-up in
`uniflo-api/docs/phase-5/` as `task-<n>-<slug>.md` (what was built, decisions,
deviations, how to verify), mirroring Phase 3/4.

---

## Track 1 — Structured programme selection

### Task 1 — `programme_id` FK migration + model wiring
**Branch:** `feature/programme-id-fk`

The structured-selection spine: link applications and their choices to the catalogue
without breaking the free-text path.

- [ ] Add nullable `programme_id: Optional[uuid.UUID]` FK → `programmes.id` to
  `app/models/application.py` (indexed). Keep `programme: str` as-is (denormalised name
  + back-compat).
- [ ] Add the same nullable `programme_id` FK to `app/models/application_choice.py`
  (indexed). `programme` string stays the source of the per-choice display name.
- [ ] One Alembic migration adding both columns + FKs. **Additive, reversible, no
  backfill** (existing rows get `NULL`). Apply via `command.upgrade()` against prod;
  record the new head in `CLAUDE.md`'s migration chain.
- [ ] Model-import smoke test only; the contract logic is Task 2.

**Squash commit:** `feat: add nullable programme_id FK to applications and choices`

---

### Task 2 — Application contract accepts + returns `programme_id`
**Branch:** `feature/application-programme-id`

Wire the FK into the create/read contract behind the locked seam.

- [ ] `schemas.py`: `ApplicationCreate` gains optional `programme_id` and
  `additional_programme_ids` (cap mirrors `MAX_ADDITIONAL_PROGRAMMES = 2`; same length
  rule as `additional_programmes`).
- [ ] `service.py` create path: when an id is supplied, **load the programme, assert it
  is active and belongs to `university_id`** (404/422 with a plain `detail` string
  otherwise), and **set `programme` from the catalogue name** (id is authoritative;
  ignore the client's free-text name for that slot). When no id is supplied, behave
  exactly as today (`programme_id = NULL`, validate the free-text string). Persist
  per-choice `programme_id` onto `application_choices`.
- [ ] `ApplicationRead.programme_id` and `ApplicationChoiceRead.programme_id` returned
  (nullable), matching Appendix A so the OpenAPI spec is the contract Partner A
  regenerates from.
- [ ] Tests (`tests/test_applications_endpoints.py`): id-only create (name derived from
  catalogue), free-text-only create (unchanged, `programme_id` null), id-not-of-this-
  university rejected, inactive-programme rejected, mixed primary-id + additional-ids.

**Squash commit:** `feat: accept and return programme_id on applications`

---

### Task 3 — Catalogue endpoint: confirm picker-readiness
**Branch:** `feature/catalogue-picker-ready` *(small — may fold into Task 2 if trivial)*

`GET /universities/{id}/programmes` already returns faculty groups with `close_date`,
and each item carries `qualification_type`, `duration_years`, `notes`, `combination`.
Confirm it gives the picker everything it needs; add only what is missing.

- [ ] Verify it returns **only active programmes for the active intake year** (it does —
  confirm with a test) and is **public** (the picker fetches it without a JWT, same as
  the universities list).
- [ ] If the picker needs a per-programme open/closed flag distinct from the faculty
  `close_date`, decide whether it derives from `close_date` on the frontend (preferred,
  no backend change) or needs a field. Default: **no backend change** — surface the
  faculty `close_date` and let the frontend compute "closed".
- [ ] If nothing is missing, this task is a confirming test + a one-line note in the
  Task 2 write-up rather than a separate PR. Do not add fields speculatively.

**Squash commit:** `test: confirm catalogue endpoint serves the structured picker`

---

## Track 2 — Applicant-type inclusivity

### Task 4 — `grade_12_final` record type + best-available ordering
**Branch:** `feature/grade-12-final-record-type`

Make the completed/final NSC a first-class record. **No migration** (plain string
column) — confirm that before relying on it.

- [ ] Add `GRADE_12_FINAL = "grade_12_final"` to `RecordType` in
  `app/api/academic_records/schemas.py`.
- [ ] Update the **best-available** record resolution (in the recommendation service,
  and anywhere else that ranks records) to
  `grade_12_final > grade_12_june > grade_12_april > grade_11_final`.
- [ ] Confirm the `(student_id, record_type)` unique constraint still lets a student
  hold a `grade_12_final` record alongside the others (it does — it is keyed on the
  pair). No change to academic-records CRUD beyond accepting the new enum value.
- [ ] Confirm `GET /recommendations` works unchanged when the chosen/best record is
  `grade_12_final` (the matcher reads marks, not the type) and that `record_type_used`
  echoes `grade_12_final`.
- [ ] Tests: a `grade_12_final` record is accepted; best-available picks it over a
  June/April/Gr11 record; recommendations compute against it; OpenAPI enum now includes
  `grade_12_final`.

**Squash commit:** `feat: add grade_12_final academic record type`

---

### Task 5 — De-assume "current learner": completed-matric automation (UP first)
**Branch:** `feature/inclusivity-automation-up`

The substantive inclusivity work. Today a server guard fails the run for anyone not
"Currently in Grade 12" (mirrored on the frontend as `isAutomationBlocked`). The
walkthroughs mapped the **completed-matric / gap-year** portal branch; teach the
automation to take it, and relax the guard **only** for the applicant types the portals
can now handle. Ship **UP end-to-end first** (proves the pattern), exactly as Phase 4
shipped UP first.

- [ ] **Branch selection plumbing (shared, not per-portal):** derive the portal
  applicant branch from the student's record type + `current_activity`
  (`grade_12_final` / gap-year → completed-matric branch; `grade_11_final` or
  `Currently in Grade 12` → current-learner branch). Put this in one place the adapters
  read, so each adapter only implements *its* branch fields.
- [ ] **Relax the guard:** permit completed-matric / gap-year through the apply path
  (the server check that currently fails with `form_submit_failed`). Keep blocking the
  genuinely-unsupported types (At university / transfer; postgrad). Coordinate the exact
  permitted set with Partner A so the frontend gate matches.
- [ ] **UP adapter — completed-matric branch:** per `docs/phase-3/portal-research/up.md`
  and `up.fields.json`, fill the completed-matric path (Highest grade = Grade 12 →
  Examination Number field; the completed-matric Exemption Type — Admit to Bachelor's /
  Certificate / Diploma). Reuse the now-known option sets; do not re-walk.
- [ ] Tests with **synthetic completed-matric students** (extend
  `tests/fixtures/synthetic_students.py`): branch selection picks the completed-matric
  path; the UP adapter's field mapping produces the completed-matric fields; the guard
  permits the type. Do **not** drive a live portal in CI.

**Squash commit:** `feat: support completed-matric applicants on the UP automation`

---

### Task 6 — Remaining portals' completed-matric branch (one per branch)
**Branches:** `feature/inclusivity-automation-<uni>` per portal

Repeat Task 5's adapter work for UJ, Wits, UCT — one branch and one PR each. The shared
plumbing and the guard already exist, so each is the per-portal branch fields plus
tests. Use the mapped branch, never a re-walk:

- [ ] **UJ** — Page C endorsement = completed/final entry (not "CURRENTLY IN GR.12");
  see `uj.md` + `uj-field-options.json`.
- [ ] **Wits** — Current School Status = "Completed Grd 12 OR Upgrading"; see `wits.md`
  + `wits.fields.json`.
- [ ] **UCT** — Step 5 completed-matric (prior-year) branch + Step 7 "Post School
  Activity" fields; see `uct.md` + `uct.fields.json` (this branch was walked
  end-to-end on 2026-06-21 as a 2024 gap-year applicant — the richest reference).

For each: synthetic completed-matric test, write up in
`docs/phase-5/task-6-<uni>.md`. **Minimum bar:** UP shipped and verified; the others
land as each adapter is extended. Correct branch handling over coverage.

**Squash commit:** `feat: support completed-matric applicants on the <uni> automation`
(one per PR)

---

## Phase 5 Checkpoint (backend)

Verify against the live dev backend (no live portal submissions):

- [ ] Migration applied to prod; `applications` and `application_choices` carry a
  nullable `programme_id`; existing rows are `NULL` and still readable.
- [ ] `POST /applications` with a `programme_id` of the posted university stores the FK
  and derives the name; a free-text-only post still works with `programme_id = NULL`; an
  id from the wrong university is rejected.
- [ ] `GET /universities/{id}/programmes` serves the picker (active programmes, faculty
  groups, `close_date`) for all four universities.
- [ ] A `grade_12_final` record is accepted; `GET /recommendations` matches against it
  and echoes `record_type_used = "grade_12_final"`; best-available prefers it.
- [ ] A completed-matric / gap-year applicant is **permitted** by the apply guard
  (frontend gate agrees); At-university / transfer / postgrad still blocked.
- [ ] UP completed-matric branch verified end-to-end against a **synthetic** applicant
  (adapter field mapping inspected; **not** a live submit). Other portals as their
  branches land.
- [ ] OpenAPI spec regenerated and deployed so Partner A can run `npm run types:api`.
- [ ] `ruff` + `pytest` green.

---

## Cross-repo sequencing (per workspace `CLAUDE.md`)

Per track: backend PRs first → Render deploy → (Task 1 only) `command.upgrade()` against
prod → Partner A runs `npm run types:api` → frontend PR. Reference the sibling PR in each
description. No `Co-Authored-By`, no Claude attribution on commits/PRs. Track 1 and
Track 2 are independent; ship Track 1 first (no live-portal risk).

---

## Environment Variables for Phase 5

None new. The FK and record type read existing tables; the automation branches reuse the
existing portal config and the existing automation env. No AI key/config changes — the
recommendation path stays pure matching, and the completed-matric branch is a navigation
change, not a new AI capability.

---

## What Is Explicitly Out of Scope for Phase 5

- **Transfers / tertiary records** — deferred to post-launch. Needs a tertiary record
  model and case-by-case, university-specific admission the NSC matcher can't do well.
  The walkthroughs note the branch exists; do not build it.
- **Postgraduate applications** — out (more complex admission logic; revisit after the
  undergraduate experience incl. transfers is complete). The walkthroughs do not map
  postgrad paths.
- **Repeaters / matric upgraders as a distinct branch** beyond what `grade_12_final`
  covers — if a portal treats "upgrading" differently from "completed", capture it as a
  follow-on, not a Phase 5 blocker.
- **Per-faculty/programme deadline enforcement** in the application-deadline check.
  `faculties.close_date` exists and the picker surfaces it (frontend), but making the
  *server-side* deadline guard prefer the faculty/programme date over
  `universities.close_date` (UP Vet Science 31 May) is a small follow-on, not required
  for the picker to ship. Flag it; build it only if a near deadline forces it.
- **Beta hardening** (POPIA review, security audit, load test, paid-tier migration) —
  the build-plan's separate phase; not this work.
- **Recommendation-engine changes** — the matcher is unchanged by inclusivity; a
  `grade_12_final` record matches like any other NSC record.

---

## Risks and Open Questions

- **Resolve before Task 2:** confirm with Partner A that `programme_id` is authoritative
  over the client-sent name (the backend overwrites `programme` from the catalogue), so
  the two repos don't disagree about which wins.
- **Resolve before Task 4:** the best-available order with `grade_12_final` at the top —
  agree with Partner A before they wire labels and the record-type selector.
- **Resolve before Task 5:** the exact `current_activity` set the apply guard now
  permits. The frontend `isAutomationBlocked` and the server guard **must** list the
  same types or a student passes one gate and fails the other.
- **Automation is the real cost.** The completed-matric branch differs per portal and
  the portals change silently. The walkthroughs give a point-in-time map; treat each
  adapter branch as tested-but-fragile and keep the synthetic-student tests as the
  tripwire. Correct branch handling on UP first beats half-working coverage on four.
- **No migration for `grade_12_final` depends on the column staying a plain string.**
  Verify `academic_records.record_type` is still `str` (not promoted to a PG enum) at
  build time; if it ever became an enum, Task 4 gains a migration.
- **`programme_id` ↔ portal study-choice code reconciliation** (per
  `portal-walkthroughs-plan.md`): the catalogue key is
  `(university_id, qualification_code, intake_year)`; some portals' study-choice codes
  differ from the prospectus code. Structured selection stores the *catalogue* id; if a
  portal needs its own code, store it separately (a later `portal_code` column) rather
  than overwriting the canonical key. Not built here, but don't design it out.

---

## Appendix A — contract deltas (locked)

```python
# app/api/applications/schemas.py  — additions only

class ApplicationChoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    choice_number: int
    programme: str
    programme_id: Optional[uuid.UUID] = None   # NEW — nullable catalogue FK
    eligible: Optional[bool] = None

class ApplicationRead(BaseModel):
    # ...unchanged fields...
    programme: str
    programme_id: Optional[uuid.UUID] = None   # NEW — nullable catalogue FK
    # ...

class ApplicationCreate(BaseModel):
    university_id: uuid.UUID
    programme: str                              # still required (display + back-compat)
    programme_id: Optional[uuid.UUID] = None    # NEW — when set, name derived from it
    additional_programmes: Optional[list[str]] = None
    additional_programme_ids: Optional[list[uuid.UUID]] = None  # NEW, parallel + capped
    application_year: int
```

```python
# app/api/academic_records/schemas.py

class RecordType(str, Enum):
    GRADE_11_FINAL = "grade_11_final"
    GRADE_12_APRIL = "grade_12_april"
    GRADE_12_JUNE = "grade_12_june"
    GRADE_12_FINAL = "grade_12_final"   # NEW — completed/final NSC (gap-year, etc.)
```

`GET /universities/{id}/programmes` (catalogue) and `GET /recommendations` are
**unchanged** in shape — they already carry everything the picker and matcher need.
