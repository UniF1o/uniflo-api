# Task 2 — Scoring + matching engine

**Branch:** `feature/recommendation-engine` · **PR:** #54 (merged)

## What was built
`app/api/recommendations/scoring.py` — a pure module (no DB, no network), fully unit-tested.

- `compute_aps(subjects, method="up_aps")` — `up_aps` = sum of NSC achievement levels of the **best 6 subjects excluding Life Orientation**; the percentage→level band (80–100→7, …) is documented inline and used when `nsc_level` is absent. Methods are dispatched by `university.scoring_method`.
- `evaluate(subjects, aps, programme) -> MatchResult` — returns `status` (`qualifies | borderline | not_yet`) and `unmet_rules` (each a `{requirement, have, shortfall}` triple phrased for a student and rendered verbatim by the frontend).
- Borderline constants: `APS_BORDERLINE_MARGIN = 2`, `SUBJECT_BORDERLINE_MARGIN = 5`.
- `tests/test_recommendation_scoring.py` — truth tables, using the UP BEng Civil `12136017` (APS 33) vs `12130017` (APS 35) pair so the tests mirror the portal's live gate.

## Key decisions / landmines handled
- Match by exact frozen NSC name; **`Mathematical Literacy`/`Technical Mathematics` are never `Mathematics`**; `English Home Language` and `English First Additional Language` stay distinct (a rule lists whichever it accepts).
- **Life Orientation excluded** from the best-6 APS.
- A record with **fewer than 6 subjects** computes on what's there (provisional, never errors).
- Human-readable `unmet_rules` strings are part of the contract.

## Deviations from plan
The engine was extended additively in Task 5 (all backward-compatible; `up_aps` untouched):
- **Per-option subject levels** (`requirements.subject_rules[].options`) and **conditional APS** (`requirements.aps_rule`) — UJ (`task-5-uj.md`).
- **`wits_aps`** — 8-point scale + bonus + LO weighting (`task-5-wits.md`).
- **`uct_fps`** — percentage-sum, faculty-aware FPS — plus a **per-method borderline margin** (`APS_BORDERLINE_MARGIN_BY_METHOD` / `aps_margin_for`) and an `fps` recompute branch in `evaluate` (`task-5-uct.md`).

## How to verify
- `pytest tests/test_recommendation_scoring.py tests/test_wits_scoring.py tests/test_uct_scoring.py` green.
- `ruff check .` clean.
