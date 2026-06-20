# Task 5 — Wits programmes

**Branch:** `feature/programmes-wits` · **PR:** #58 (merged) · **Seeded to prod**

## What was built
- `data/programmes/wits.json` — **56 full-time bachelor degrees across all 5 faculties** (Commerce/Law/Management, Engineering & Built Environment, Health Sciences, Humanities, Science). intake_year 2027; default close 2026-09-30 with a Health Sciences override (2026-06-30).
- **New scoring method `wits_aps`** in `scoring.py`:
  - 8-point scale (90–100 → 8); marks < 40% score 0.
  - **+2 bonus** on English and Mathematics, only at ≥ 60%.
  - **Life Orientation** at reduced weight (8→4, 7→3, 6→2, 5→1, else 0).
  - APS = **best seven subjects including Life Orientation** (LO + best 6 others). Max 56 (`_APS_MAX`).
- `tests/test_wits_scoring.py` — 7 truth-table tests.
- Registry entry `wits.json → University of the Witwatersrand / wits_aps`.

## Key decisions
- **Health Sciences programmes have no APS** (selection by Composite Index = 60% academics + 40% NBT) → `min_aps` null; they gate on subject rules only.
- NBT / audition / job-shadowing captured as non-gating `notes`; *"Life Sciences AND/OR Physical Sciences"* encoded as an at-least-one `options` rule.
- **Source:** the 2026 SLO summary was superseded by the authoritative **2027 Guide for Undergraduate Applicants**, which confirmed the best-7-incl-LO rule.
- Wits publishes no programme codes here → `qualification_code` null.

## How to verify
- Prod: **Wits = `wits_aps`, 5 faculties, 56 active**.
- `pytest tests/test_wits_scoring.py` green; `check_prospectus_year.py` current.
