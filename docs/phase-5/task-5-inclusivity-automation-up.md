# Task 5 — Completed-Matric Automation: UP

**Branch:** `feature/inclusivity-automation-up`
**Status:** complete

---

## What was built

### Branch selection plumbing (shared, `app/automation/mapping.py`)

Added two functions used by all portals:

**`_applicant_branch(profile, records) -> str`** — returns `"completed_matric"` or `"current_learner"`. Primary signal: a `grade_12_final` record is present. Fallback signal: `current_activity` matches gap/employ/work/occupat/complete patterns. Pure and side-effect free; called by each per-portal mapping.

**`_guard_applicant_type(profile, slug, records)`** — replaces `_require_current_schooling`. Universally blocks at-university, upgrader, and postgrad. For UP (`_COMPLETED_MATRIC_SLUGS`), permits completed-matric/gap-year and returns early. For UJ/UCT/Wits, the old strict block for completed-matric activity patterns is preserved until Task 6 extends those adapters.

Also updated `_matric_year` to prefer `grade_12_final` records alongside `april/june` (the year comes from the final certificate, not the intake year − 1).

### UP adapter mapping (completed-matric branch)

`_up_mapping` now calls `_applicant_branch` and conditionally sets:

| Field | current_learner | completed_matric |
|---|---|---|
| `tell_us_more` | "I am currently still in high school" | "I am unemployed…" or "I am working/employed…" (from current_activity) |
| `highest_grade` | "Grade 11" | "Grade 12" |
| `exemption_type` | "Currently busy with schooling" | "Admit to Bachelor Studies" |
| subjects / school | from `grade_11_final` record | from `grade_12_final` record (fallback to gr11 if absent) |

The `upload_documents` method in the UP adapter already handles completed-matric correctly: it prefers `GRADE11_RESULTS` but falls back to `MATRIC_RESULTS` (row 3 in the fixed upload index), so a completed-matric student who uploads `MATRIC_RESULTS` gets the right row without any adapter change.

Added `_up_tell_us_more_completed(profile)` to derive the `tell_us_more` value from `current_activity` (employ/work/occupat → working option; all else → unemployed option).

### Fixtures (`tests/fixtures/synthetic_students.py`)

Added three new exports:
- `SYNTHETIC_COMPLETED_MATRIC_PROFILE` — gap-year student with `current_activity = "Gap Year"` and `exam_number`
- `SYNTHETIC_GRADE_12_FINAL_RECORDS` — a `grade_12_final` record with four subjects and explicit `percentage` + `nsc_level` fields
- `SYNTHETIC_COMPLETED_MATRIC_DOCUMENTS` — `[ID_COPY, MATRIC_RESULTS]`

### Tests (`tests/test_mapping_completed_matric.py`)

26 new tests covering:
- `_applicant_branch`: grade_12_final record wins over activity; gap/work activity patterns trigger completed_matric; current_learner preserved for Grade 12 students; no activity → current_learner
- `_guard_applicant_type`: permits current_gr12/gap_year/employed for UP; blocks at-university/upgrader for all portals; blocks completed-matric for UJ/Wits/UCT
- UP mapping: all branch-conditional field values (highest_grade, exemption_type, tell_us_more, subjects, school, final_school_year)

Updated `tests/test_mapping_cross_portal.py`:
- Renamed `test_non_school_activity_fails_fast` → `test_non_school_activity_fails_fast_for_non_up_portals` (excludes UP from the loop)
- Added `test_gap_year_permitted_for_up` confirming the relaxation

---

## Decisions

- **`grade_12_final` record beats `current_activity`** for branch selection. A student who has uploaded their final results is unambiguously completed-matric regardless of what `current_activity` says.
- **`exemption_type = "Admit to Bachelor Studies"`** is the typical UP value for completed NSC applicants. The adapter uses `_select_label_best` (fuzzy match) so small portal text variations are handled at runtime without a code change.
- **`tell_us_more` derived from `current_activity`** rather than hardcoded — "Gap Year" / unspecified → unemployed option; "Working" → employed option. This keeps the form accurate for both gap-year and working applicants.
- **`upload_documents` unchanged** — the existing `GRADE11_RESULTS or MATRIC_RESULTS` fallback chain already handles completed-matric without modification.
- **`_COMPLETED_MATRIC_SLUGS` frozenset** makes the guard extension to UJ/UCT/Wits a one-liner each in Task 6.

## Blocked / out of scope

- UJ, Wits, UCT completed-matric branches → Task 6 (one branch/PR each)
- Upgrader (repeating subjects) → separate branch, post-Phase-5
- Disability detail, disability detail modal → data model gap, documented in up.md
- Payment gate → R300 still stops at `HumanActionRequiredError` regardless of branch

## How to verify (non-live)

```bash
pytest tests/test_mapping_completed_matric.py -v   # 26 new tests
pytest -v                                           # full suite (440 pass)
ruff check .                                        # clean
```

For a real completed-matric student flowing through the UP adapter:
- Set `FAKE_AUTOMATION=false`, `AUTOMATION_ALLOW_SUBMIT=false` (form filled, not submitted)
- POST /applications with a student whose `academic_records` contains a `grade_12_final` row and whose documents include `MATRIC_RESULTS`
- Inspect the field mapping: expect `highest_grade=Grade 12`, `exemption_type` containing "Admit", `tell_us_more` matching the student's activity
