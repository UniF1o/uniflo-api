# Task 5 — UCT programmes (Faculty Points Score)

**Branch:** `feature/programmes-uct` · **PR:** #59 (merged) · **Seeded to prod**

## What was built
- `data/programmes/uct.json` — **29 undergraduate degrees across all 6 faculties** (Commerce, Engineering & the Built Environment, Health Sciences, Humanities, Law, Science). intake_year 2027, close 2026-07-31.
- **New scoring method `uct_fps`** in `scoring.py` — the most bespoke:
  - **APS = sum of percentages** (English + 5 best other subjects, excl Life Orientation; marks < 40% score 0; out of 600).
  - **FPS is per-programme** via a `requirements.fps` block (`required[]`, `double[]`): Commerce/Eng/Hum/Law FPS = APS; **Science doubles Maths + Physical Sciences** (/800); required subjects force-included in the best-5. `evaluate()` recomputes the score when an `fps` block is present.
  - **Per-method borderline margin** (`uct_fps` = 5 pts; `aps_margin_for`); `_APS_MAX[uct_fps] = 600`.
- `min_aps` = each programme's **Band A "guaranteed admission" FPS** (BCom 435, Engineering 500, Science 660, MBChB sub-min 450, LLB 500).
- `tests/test_uct_scoring.py` — 7 tests. Registry entry `uct.json → University of Cape Town / uct_fps`.

## Key decisions / limitations (documented in notes)
- **Health FPS (/900 = APS + NBT) is uncomputable** — UniFlo captures only an NBT *reference* (`nbt_reference`/year/date), not AL/QL/MAT scores. Health gates on the documented **sub-minimum APS** (/600); a "qualifies" there means "meets the floor," not the competitive band.
- **WPS / redress** (disadvantage-weighted score that drives selection) needs UCT's internal 0–10%/0–20% factor; UniFlo stores the raw `redress_factors` answers but not the algorithm → `min_aps` uses the **unweighted** Band A FPS.
- **General degrees that admit to one degree with majors chosen within** list their majors/specialisations in `notes` for discoverability (Science BSc ~22 majors; Commerce BCom/BBusSc; Humanities BA/BSocSc) — without implying separate admission programmes. CS/Statistics and Actuarial (different requirements) are split into their own entries.
- Technical Mathematics/Science are not accepted substitutes; no programme codes published → `qualification_code` null.

## Status
- **Merged (#59) and seeded to prod** — UCT = `uct_fps`, 6 faculties, 29 active. Seeded only after merge + deploy (the deployed engine needed `uct_fps`).

## How to verify
- `pytest tests/test_uct_scoring.py` green; `check_prospectus_year.py` shows uct.json current.
- Prod: UCT = `uct_fps`, 6 faculties, 29 active programmes.
