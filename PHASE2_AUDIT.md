# Phase 2 Audit — 2026-05-15

Deep-dive review of the codebase after the Phase 2 work shipped (universities,
applications, application_jobs, fake automation, self-healing user sync).
Tests: 59 passed before changes, 59 passed after. `ruff check .` clean.

Each change is paired with the file(s) touched and the reasoning.

---

## 1. Critical / build hygiene

### `requirements.txt` — UTF-16 BOM regression + transitive bloat
**Issue.** The file was UTF-16 LE with a BOM and CRLF line endings (3,176 bytes,
86 lines of `pip freeze` output). This is the exact bug fixed in Phase 1 — it
regressed, almost certainly because someone re-ran `pip freeze > requirements.txt`
in a PowerShell session, which produces UTF-16 by default. `pip install -r` on
Linux (the GitHub Actions runner) parses the BOM as garbage and fails.

Beyond the encoding, the file was a transitive-dep dump: 80+ packages including
`cffi`, `pycparser`, `h2`, `hpack`, `hyperframe`, `propcache`, `multidict`,
`pyiceberg`, `pyroaring`, `mmh3`, `zstandard`, `fsspec`, etc. — almost all of
which are indirect deps of `supabase`, `cryptography`, or `pydantic`. Listing
them by hand is pointless and locks the API to specific patch versions of
internals that the direct deps could otherwise resolve fresh.

**Fix.**
- Rewrote `requirements.txt` as proper UTF-8 with LF endings, slim to **17
  direct dependencies**, grouped by concern (web, data, validation, auth,
  external).
- New `requirements-dev.txt` with `-r requirements.txt` + pytest, pytest-asyncio,
  ruff, black.
- `.github/workflows/backend.yml` switched from `pip install -r requirements.txt`
  to `pip install -r requirements-dev.txt` so CI gets the test/lint tools too.
- Added a header comment in `requirements.txt` warning against `pip freeze`.

### `alembic/env.py` — model registry was empty
**Issue.** `target_metadata = SQLModel.metadata` only sees tables for models
that have been imported by the time autogenerate runs. The file imported
`app.config` but nothing from `app.models`, so `alembic revision --autogenerate`
would have produced empty migrations forever. (The existing migrations are
hand-curated, which masked the bug.)

**Fix.** Added `from app import models  # noqa: F401` — that one import
triggers `app/models/__init__.py` which already re-exports every table. Future
autogenerate will now see all of them.

---

## 2. Code quality

### Duplicate Pydantic schemas — `app/api/profiles/schemas.py`
**Issue.** `StudentProfileCreate` and `StudentProfileUpdate` had byte-identical
field definitions (9 optional fields). Two copies, one source of truth needed.

**Fix.** Renamed the implementation to `StudentProfileWrite` and aliased both
old names to it (`StudentProfileCreate = StudentProfileWrite`,
`StudentProfileUpdate = StudentProfileWrite`). Router imports untouched; tests
unchanged. OpenAPI will now show a single `StudentProfileWrite` schema
referenced by both endpoints, which is cleaner for the generated TS types too.

### Frivolous comments
**Issue.** `app/api/profiles/router.py` had trailing emoji decorations on each
route (`# Creates profile :)`, `# Gets student profile details <3`,
`# Updates Student profile details`). `app/api/automation/background.py` had
`"so CEO(our short king) can watch status transitions"`.

**Fix.** Removed. The route names are self-documenting; the inside joke isn't
appropriate for an external-facing OpenAPI-generating file.

### Duplicate `Limiter` instance — `app/api/universities/router.py`
**Issue.** `main.py` created its own `Limiter`, registered it on `app.state`,
and bound the exception handler to it. `universities/router.py` then created a
**second** `Limiter` and used its `@limiter.limit("60/minute")` decorator.
Two limiters means two independent in-memory storages — the rate-limit error
handler is wired to the first limiter, but counters live on the second. In
practice it still works under SlowAPI because the decorator path doesn't go
through `app.state`, but the configuration is incoherent and would silently
break the day someone moves storage to Redis.

**Fix.** New module `app/rate_limit.py` exporting a single `limiter` instance.
Both `main.py` (for `app.state.limiter` registration) and
`universities/router.py` (for the decorator) now import from there.

### `pyproject.toml` — no Python version pin
**Issue.** No `[project]` table at all; nothing declares the Python version the
codebase supports. CI happens to use 3.12, but nothing enforces that locally.

**Fix.** Added `[project]` block with `requires-python = ">=3.12"` plus a
matching `name` / `version`. Ruff / black / pytest config preserved.

---

## 3. Items reviewed but intentionally left alone

| Item | Reason |
|------|--------|
| Empty alembic revision `5f641ecfb811` | Already applied to production. Removing it would mean rewriting applied history. The chain is messy but correct; leave it. |
| `application_year` hard-coded to `(2026, 2027)` in `applications/schemas.py` | Likely a product decision (Phase 2 launch window). Will surface as a 422 the moment someone tries 2028 — easy to spot, easy to fix in one place. Worth a follow-up but not silently changing under the team's feet. |
| `AcademicRecord` model | No router/service references it. Looks like Phase 1 scaffolding for a future endpoint. Keep — the table exists in prod. |
| `webhooks/user-created` and `webhooks/user-updated` redundant with `ensure_user_synced` middleware | Webhooks fire on Supabase signup, before any auth'd request reaches the API. They guarantee a `public.users` row exists *immediately*. `ensure_user_synced` is defense in depth for missed webhook deliveries. Both layers are correct. |
| `get_student_profile` returns 403 in `applications/service.py` vs profiles' 404 | The 403 is a deliberate contract signal: "complete your profile before applying". Tests assert it. Changing it would break the frontend's expected error code. |
| `application.latest_job = job` runtime attribute assignment in `applications/service.py` | Works because SQLModel inherits from Pydantic and allows arbitrary attribute set; the response schema declares `latest_job` so it's serialised. The "proper" fix is a SQLAlchemy relationship, but that's a Phase 3 schema concern. |
| `created_at = datetime.now(timezone.utc)` literal in `Application.__init__` (router) overriding the model default | Cosmetic. Both paths produce the same value; the explicit call documents intent. |
| `scripts/seed_universities.py` uses `print()` instead of `logging` | Operator script run by hand. `print` is fine here. |
| Sentry `traces_sample_rate=1.0` | Fine for low-traffic Phase 2. Worth tuning down when prod traffic grows; not blocking. |
| SlowAPI deprecation warning (`asyncio.iscoroutinefunction`) | Library bug — not ours. Will go away in a future slowapi release. |

---

## 4. README

Replaced the 7-line placeholder (just an OpenAPI URL hint) with a full
`README.md` covering:

- One-paragraph project description
- Stack table (FastAPI / SQLModel / Alembic / Supabase / SlowAPI / Sentry)
- Repository layout (per-module)
- Quick-start (clone → venv → install → `.env` → migrations → run)
- Environment-variable reference
- Common commands (lint, tests, alembic, openapi-typescript)
- Auth model (5 numbered steps: JWKS verification flow + public-route bypass)
- Document storage (private bucket + signed URLs explanation)
- Migration chain (linear list, head = `a3b2c1d4e5f6`)
- Testing model (mocked sessions, no real DB)
- Deployment (Render + CI deploy gate)

---

## 5. Files changed

```
M  .github/workflows/backend.yml   pip install -r requirements-dev.txt
M  README.md                       full rewrite
M  alembic/env.py                  import app.models for autogenerate
M  app/api/automation/background.py  remove "CEO our short king" comment
M  app/api/profiles/router.py      strip emoji comments
M  app/api/profiles/schemas.py     dedupe Create/Update -> Write alias
M  app/api/universities/router.py  use shared limiter
M  app/main.py                     use shared limiter
M  pyproject.toml                  add [project] + requires-python pin
M  requirements.txt                UTF-8 + slim direct deps only
A  PHASE2_AUDIT.md                 this doc
A  app/rate_limit.py               single shared Limiter
A  requirements-dev.txt            -r requirements.txt + test/lint deps
```

---

## 6. Verification

```bash
ruff check .         # All checks passed!
pytest -q            # 59 passed in ~10s
alembic history      # chain intact, head = a3b2c1d4e5f6
```

No behavioural changes to any endpoint. OpenAPI surface unchanged except the
`StudentProfileCreate` / `StudentProfileUpdate` schemas collapse to a single
`StudentProfileWrite` (frontend TS regen is a no-op if you import both names —
they're now the same class).
