# Phase 6 — Applicant-type + citizenship coverage (backend)

> Backend half of a cross-repo plan. The frontend half lives in
> `uniflo-web/docs/phase-6/applicant-type-citizenship-plan.md`.
> **Status: plan only. No implementation until research PRs #80 (UJ) and #82 (UP) are merged.**

## Context

The Phase 3 portal-research effort (UCT #78, Wits #79, UJ #80, UP #82) mapped how each
university portal's application form *branches* by applicant type and citizenship. The adapters
have not yet caught up to that research.

Today `app/automation/` handles **still-in-Grade-12** and a single collapsed **completed-matric**
branch (which also absorbs gap-year/employed) for **SA citizens with an SA ID only**.
`_guard_applicant_type` in `app/automation/mapping.py` *hard-blocks* upgrading/repeating,
at-university/transfer and postgrad, and there is **no international/passport path anywhere** — no
passport branch in any adapter, and no passport/permit columns in the schema.

**Goal:** the adapters fill each portal correctly for still-in-G12, completed-matric, gap-year,
employed, **upgrading/repeating (newly unblocked)**, and **international/non-SA citizen with
passport + permit (newly added)**. At-university/transfer and postgrad stay explicitly blocked with
a clear "apply manually" message (research scoped transfers out as note-fields-only).

### Decisions (locked)
1. **Tracks this round:** add upgrading/repeating + international/passport; keep
   at-university/transfer + postgrad blocked.
2. **Citizenship model:** full residency taxonomy — `citizenship_status`
   (SA Citizen / Permanent Resident / Refugee / Asylum Seeker / International) + `passport_number`
   + `study_permit_type` (UJ's 17-option permit LOV as the canonical set). `nationality` (country)
   and `is_sa_citizen` already exist and are retained.
3. **Migration:** additive, all-nullable, reversible; apply to prod via `alembic upgrade head`
   **only after the PR merges** (`DATABASE_URL` = production).

### Scope notes from research (must respect)
- **UP international is gated at SIGNUP** ("Identify me by: Passport Number"), not in-app — the
  current emailed-login UP adapter cannot reach it. **UP international stays manual/blocked**; UP
  still gains the upgrading branch. UJ, UCT, Wits get full international.
- **Stellenbosch** has no adapter and is reCAPTCHA-blocked — out of scope entirely.

---

## Workstream A — Data model

New, all-nullable columns on `student_profiles` + enums + schema exposure. The profile service
auto-round-trips new fields via `model_dump(exclude_unset=True)` + `setattr`, so no per-field
service wiring is needed.

**A1. Model** — `app/models/student_profile.py`: add nullable columns
`citizenship_status: Optional[str]`, `passport_number: Optional[str]`,
`study_permit_type: Optional[str]`. (`nationality`, `is_sa_citizen`, `id_number` already exist.)

**A2. Migration** — `alembic/versions/<rev>_citizenship_passport_fields.py`
- `down_revision = "b7c653dd1cee"` (current head per `CLAUDE.md`).
- Three `op.add_column("student_profiles", sa.Column(..., sa.Text(), nullable=True))`; symmetric
  `downgrade()`. Follow the `c5d4e3f2a1b0` pattern exactly.
- **Do not apply locally during dev** (prod DB). Apply only after merge.

**A3. Enums + schema** — `app/api/profiles/schemas.py`
- Add `CitizenshipStatusEnum` (SA Citizen / Permanent Resident / Refugee / Asylum Seeker /
  International) and `StudyPermitTypeEnum` (the 17 codes from `uj-field-options.json`
  `oapStudyPermit`).
- Add the three fields to `StudentProfileWrite` and `StudentProfileResponse`.
- Add a `model_validator` enforcing **conditional requirement**: when `citizenship_status` is
  International / Refugee / Asylum Seeker / Permanent Resident, `passport_number` is required (and
  `study_permit_type` for International). Must NOT affect SA-citizen submissions.
- Leave `REQUIRED_PROFILE_FIELDS` unchanged (additive-nullable convention); conditional rules live
  in the validator above.
- `CurrentActivityEnum` already has `UPGRADING = "Upgrading matric"` — no change.

---

## Workstream B — Mapping layer (`app/automation/mapping.py`)

The single highest-leverage file. Two orthogonal axes: **schooling status** and **citizenship**.

**B1. Unblock upgrading** — `_guard_applicant_type`
- Remove `"upgrad"` from the universal block list; keep `"universit"` and `"postgrad"` blocked.
- Update the error message to name the still-unsupported types.
- Update the partner test that currently asserts an upgrader raises (see E1).

**B2. Schooling-status branch** — `_applicant_branch`
- Add a distinct `"upgrading"` return when `current_activity` contains `"upgrad"` (checked before
  the completed/current logic). Upgraders carry a prior matric → subject source =
  `grade_12_final` (fallback `grade_11_final`), same as completed.
- Keep `completed_matric` (gap/employed/complete) and `current_learner` as today.

**B3. Citizenship resolution** — new helper `_citizenship(profile)` returning a dict of canonical
keys consumed by every portal mapper: `is_sa_citizen`, `citizenship_status`, `nationality`
(country), `passport_number`, `study_permit_type`. SA-citizen path unchanged (back-compat).

**B4. Per-portal wiring** (each `_*_mapping` already exists; extend, don't rewrite):
- **UJ** `_uj_mapping`: international = set `sa_citizen="No"`, `citizenship_code=nationality`, add
  `passport_number`, `study_permit`, explicit `gender`/`date_of_birth` (the `oapCitizenType="No"`
  reveal set per `uj-field-options.json`). Upgrading = set `upgrading="Yes"` (currently hardcoded
  `"No"`) and adjust `endorsement`/`present_activity`.
- **UCT** `_uct_mapping`: `citizenship_type` is currently `"SA Citizen" | None`; map the full set
  (International (Non-SA Citizen) / Permanent Resident / Refugee / Asylum Seeker / SA Citizen). Add
  `passport_country` (= nationality), `passport_citizenship_status`, `passport_number` for the
  Step-2 Passport Information add-row table.
- **Wits** `_wits_mapping`: set `nationality` to the real country (currently
  `"South Africa" | None`); supply `passport_number`. Add `"upgrad"` → `"Currently upgrading
  matric"` in `_wits_activity` (Step-3 driver; Step-4 derives "Completed Grd 12 OR Upgrading").
- **UP** `_up_mapping`: add the upgrading `tell_us_more`/`exemption_type` option. **Do not** add an
  international path (signup-gated). When `is_sa_citizen` is false for UP, raise the guard's
  manual-application `ValueError`.

---

## Workstream C — Adapters (`app/automation/adapters/`)

Adapters consume the new mapping keys; most already do thin `mapping.get(...)` reads. New work is
the **field-swap / conditional-reveal handling** the international branch needs.

- **`uj.py`**: handle the `oapCitizenType="No"` reveal — fill `oapPPnumber`, the `oapStudyPermit`
  LOV (17 options; fuzzy-match like other LOVs), explicit gender/DOB. Drive `oapStudUpgrade` for
  upgraders. ITS quirks already documented in `uj-field-options.json._adapter_critical_fixes`.
- **`uct.py`**: ~line 367 currently defaults `citizenship_type` to `"SA Citizen"`. For
  International, select the citizenship option, then fill the revealed **Passport Information
  add-row table** (Country / Citizenship Status / Passport Number). Guard the **AJAX hazard**:
  toggling citizenship blanks the SA-ID field — set citizenship before any ID entry.
- **`wits.py`**: nationality select **auto-sets National ID Type** — set nationality to the real
  country so the portal flips to passport, then fill the passport field. Upgrading already routes
  through the Step-3 main-activity value (`school_status` read at `wits.py:574`).
- **`up.py`**: upgrading only (new `tell_us_more`/`exemption_type` value). No international.
- `app/automation/adapters/__init__.py`: no registry change (all four portals already registered).

Every new live-only assumption gets a `[VERIFY]` comment (matching the existing convention in
`mapping.py`) to be confirmed on the first `allow_submit=False` live run.

---

## Workstream E — Testing (foolproofing before any live submit)

**E1. Mapping unit tests** (`tests/`, pure, no DB/browser — the canonical layer)
- Extend `tests/fixtures/synthetic_students.py` with an **international** profile (passport +
  permit + non-SA citizenship_status) and an **upgrader** profile.
- In `tests/test_mapping_completed_matric.py` (or new `test_mapping_international.py` /
  `test_mapping_upgrading.py`): assert `_applicant_branch` returns `"upgrading"`; assert
  `_guard_applicant_type` **no longer raises** for upgraders but **still raises** for
  at-university/postgrad and for **UP international**; assert per-portal `m.values[...]` carry the
  right passport/permit/citizenship/upgrade keys for UJ/UCT/Wits.
- **Flip the existing `_UpgraderProfile` assertion** that currently expects a `ValueError`.

**E2. Adapter unit tests** (fake Playwright `Page`/popups, no real browser)
- `test_uj_adapter.py`: seed the `oapStudyPermit` LOV + `oapCitizenType="No"` reveal from
  `uj-field-options.json` harvested rows; assert the passport/permit fields are filled and
  `oapStudUpgrade` driven.
- `test_uct_adapter.py`: fake the Step-2 citizenship select + Passport Information add-row table;
  assert SA-ID is not touched on the International branch.
- `test_wits_adapter.py`: assert nationality-driven ID-type swap fills passport.

**E4. Live foolproofing** (manual, `AUTOMATION_ALLOW_SUBMIT` unset → `FILLED`, **never submit**):
drive UJ/UCT/Wits international + upgrading against the parked Jane Doe test accounts via the
Playwright MCP, screenshot each step, resolve every `[VERIFY]` marker. Screenshots stay local
(never committed) per the project convention.

> Frontend tests (E3) are covered in the frontend plan doc.

### Offline adapter harness (Workstream F — `uniflo-testing` repo)
The adapter changes (Workstream C) are also exercised offline by the **`uniflo-testing`** repo —
aiohttp fake portals that run the real adapters with `allow_submit=False` (pass = `FILLED`). Its
fakes must replicate every new conditional reveal (UJ `oapCitizenType`/`oapStudUpgrade`, UCT Step-2
passport add-row swap, Wits nationality-driven ID type, UP upgrading exemption) or the new code
paths ship untested. Full detail in `uniflo-testing/docs/phase-6/applicant-type-citizenship-plan.md`.
Its CI (`fake-portal-tests.yml`) must run with `uniflo_api_ref = feature/applicant-type-citizenship`
so the fakes test this branch's adapters.

---

## Sequencing (dependency order)

1. **A** (data model + migration authored, not yet applied) — the contract both backend and
   frontend depend on.
2. **B** (mapping) + **C** (adapters); **E1/E2** alongside.
3. **Workstream F** (`uniflo-testing` fakes + harness) tracks **C** in lock step — its CI runs
   against this adapter branch via `uniflo_api_ref`.
4. Frontend consumes the regenerated `schema.d.ts` (see frontend doc).
5. Apply migration to prod (`alembic upgrade head`) after this PR merges.
6. **E4** live foolproofing on parked accounts; clear `[VERIFY]` markers.

Ships as `feature/applicant-type-citizenship` (same branch name in `uniflo-web`), Squash-and-Merge.

---

## Verification

- `cd uniflo-api && pytest -v && ruff check .` — all green, including the new mapping/adapter tests
  and the flipped upgrader assertion.
- After the backend is running, the frontend regenerates types; confirm `tsc` stays clean there.
- **Live (foolproofing):** E4 above — `FILLED` outcome only, no submit, screenshots reviewed.
- **Prod migration:** after merge, `alembic upgrade head`; confirm `alembic current` = new head and
  the app boots (ORM/DB in sync).

---

## Execution gating (user directive)
1. **Now:** this plan PR only.
2. **Hold:** do **not** start any implementation (Workstreams A–E) until prior research PRs
   **#80 (UJ)** and **#82 (UP)** are approved/merged.
3. **Then:** implement in the sequence above.
