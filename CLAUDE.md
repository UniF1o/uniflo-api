# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Commands

```bash
# Run dev server
uvicorn app.main:app --reload

# Tests
pytest -v

# Single test file
pytest tests/test_applications_endpoints.py -v

# Lint
ruff check .

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "describe change"
alembic downgrade -1

# Seed universities
python scripts/seed_universities.py
```

Python 3.12, venv at `.venv/`. Install deps with `pip install -r requirements-dev.txt`.

## Architecture

**UniFlo** is a FastAPI backend that lets South African school leavers apply to multiple universities through a single profile. Phase 3 (not yet built) will use Playwright bots to fill in each university portal automatically.

### Request lifecycle

1. `CORSMiddleware` → `AuthMiddleware` → route handler
2. `AuthMiddleware` (`app/api/middleware/auth.py`) verifies Supabase-issued JWTs via JWKS (RS256/ES256). It stores the decoded payload on `request.state.user` and calls `ensure_user_synced()` on every authenticated request to keep `public.users` in sync with `auth.users` as a belt-and-suspenders fallback for missed webhooks.
3. Public routes bypass auth: `/health`, `/ping`, `/openapi.json`, `/docs/*`, `/redoc/*`, `/universities/*`, and the three `/webhooks/*` endpoints. Webhooks use their own shared-secret check (`x-webhook-secret` header).
4. Unhandled exceptions are caught by a global handler that re-applies CORS headers manually — necessary because `ServerErrorMiddleware` wraps the whole app *outside* `CORSMiddleware`, so an unhandled 500 would otherwise surface to the browser as a CORS error.

### Service layer pattern

Every feature area (`profiles/`, `documents/`, `applications/`, etc.) has:
- `router.py` — FastAPI router; extracts `user_id` from `request.state.user["sub"]`, then delegates to service
- `service.py` — all DB logic; receives `Session` via dependency injection (`get_session`)
- `schemas.py` — Pydantic request/response models

Routes never touch the DB directly. Services raise `HTTPException` for domain errors.

### Data model key points

- `User` (mirrors `auth.users`) → `StudentProfile` (1:1) → `Document`, `AcademicRecord`, `Application`
- `Application` → `ApplicationJob` (many; latest job carries the automation status/error)
- `Application.status` and `ApplicationJob.status` are kept in sync: `pending → processing → submitted|failed`
- `student_profiles.user_id` references `users.id`; most service calls start by looking up the profile by `user_id`
- `Application.latest_job` is a transient attribute attached at query time — it is not a DB relationship

### Document storage

The `documents` Supabase Storage bucket is private. The DB stores `storage_path` (e.g. `<user_id>/<type>/<uuid>.pdf`); a 1-hour signed URL is minted on every read. Uploads use `SUPABASE_SERVICE_ROLE_KEY` — the anon key is rejected by Storage RLS. Storage paths use a UUID, not the user-supplied filename.

### Application automation (Phase 2 stub)

`POST /applications` enqueues `process_application()` as a FastAPI `BackgroundTask`. With `FAKE_AUTOMATION=true` (current default), it simulates a portal submission with a random delay and 80% success rate. Set `FAKE_AUTOMATION=false` to skip the stub entirely; Phase 3 will replace it with real Playwright adapter calls.

### Auth model detail

- Supabase issues RS256/ES256 JWTs; `PyJWKClient` fetches keys from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
- Three webhook endpoints (`/webhooks/user-created`, `/webhooks/user-updated`, `/webhooks/user-deleted`) are fired by Supabase Auth on user lifecycle events. `user-deleted` uses a separate `DELETE_WEBHOOK_SECRET` for least privilege.
- `SUPABASE_JWT_SECRET` is kept in config for completeness but is not used — verification is JWKS-only.

## Testing

Tests use `TestClient`, mock the DB via `app.dependency_overrides[get_session]`, patch `jwt.decode` to bypass JWKS, and patch `ensure_user_synced` via an autouse fixture in `tests/conftest.py`. No real database is touched.

Pattern for an authenticated test:
```python
with patch("app.api.middleware.auth.jwt.decode") as mock_decode, \
     patch("app.api.<module>.service.<function>") as mock_fn:
    mock_decode.return_value = {"sub": USER_ID, "email": "...", "role": "student"}
    mock_fn.return_value = ...
    response = client.get("/endpoint", headers={"Authorization": "Bearer validtoken"})
app.dependency_overrides.clear()  # always clean up
```

## Deployment

- Render Web Service; CI (`.github/workflows/backend.yml`) runs tests + lint on push/PR and fires Render's deploy hook on `main`.
- ⚠️ **`DATABASE_URL` in `.env` is the PRODUCTION database** — there is no separate dev/staging DB. Any DB command run locally (`alembic upgrade/downgrade`, scripts, ad-hoc SQL) hits production directly. Treat destructive operations with extreme care; keep migrations additive + reversible; never run an untested downgrade or a manual `DROP`/`DELETE` against it without explicit confirmation.
- Migrations are **not** auto-applied by CI. Because `.env` points at prod, `alembic upgrade head` applies to production directly (no separate Render-shell step needed).
- **Migration head: `f8a7b6c5d4e3` (applied to prod 2026-06-06).** **Always run `alembic upgrade head` immediately after creating a migration or pulling/merging a schema change — never leave a migration unapplied** (an unapplied migration leaves the app and ORM models out of sync → 500s). Chain applied to prod: `b4c3d2e1f0a9` → `c5d4e3f2a1b0` (address split + demographics) → `d6e5f4a3b2c1` (academic_records `record_type`) → `e7f6a5b4c3d2` (Phase 3 portal gap-fill: ~24 `student_profiles` fields incl. mailing-address block, NBT block, `redress_factors` JSONB; new `contacts` + `application_choices` tables) → `f8a7b6c5d4e3` (`applications.popi_consent_at` + `agreement_consent_at` consent timestamps).
