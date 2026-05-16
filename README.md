# UniFlo API

FastAPI backend for **UniFlo** -- a service that lets South African school leavers
apply to multiple universities through a single profile + document upload. The
backend stores the student profile, holds uploaded documents in private Supabase
Storage, and (in Phase 3) drives Playwright bots that fill in each university
portal on the student's behalf.

Auth is handled by Supabase; this API verifies Supabase-issued JWTs via JWKS and
keeps a mirror of `public.users` in sync with `auth.users` through webhooks +
a self-healing middleware.

Hosted at: <https://uniflo-api.onrender.com> (Render). OpenAPI spec:
<https://uniflo-api.onrender.com/openapi.json>.

---

## Stack

| Layer            | Tool                                                 |
|------------------|------------------------------------------------------|
| Web framework    | FastAPI + Uvicorn                                    |
| ORM / models     | SQLModel (SQLAlchemy 2.x under the hood)             |
| Migrations       | Alembic                                              |
| Database         | PostgreSQL (Supabase-hosted)                         |
| Auth             | Supabase JWT (RS256/ES256, verified via JWKS)        |
| File storage     | Supabase Storage (private bucket, signed URLs)       |
| Rate limiting    | SlowAPI                                              |
| Errors / tracing | Sentry                                               |
| Tests            | pytest                                               |
| Lint / format    | ruff + black                                         |

Python 3.12.

---

## Repository layout

```
app/
  main.py                 FastAPI app, middleware, router registration
  config.py               Pydantic-settings (env-driven)
  db.py                   Lazy engine + session dependency
  rate_limit.py           Single shared SlowAPI limiter
  supabase_client.py      Lazy Supabase client factory
  models/                 SQLModel tables (User, StudentProfile, Document,
                          University, Application, ApplicationJob, AcademicRecord)
  api/
    middleware/auth.py    JWT verification + ensure_user_synced
    auth/                 GET /auth/me
    profiles/             POST|GET|PATCH /profile
    academic_records/     POST|GET|PATCH /academic-records (one per student)
    documents/            POST /documents/upload, GET /documents,
                          DELETE /documents/{id}
    universities/         GET /universities, GET /universities/{id}
    applications/         POST|GET /applications, GET /applications/{id},
                          POST /applications/{id}/retry (501 stub)
    webhooks/             POST /webhooks/user-{created,updated,deleted}
    automation/           background.py -- Phase 2 fake processor
alembic/                  Migrations (one chain, head = b4c3d2e1f0a9)
scripts/seed_universities.py
tests/                    pytest suite (59 tests)
```

---

## Quick start

```bash
# 1. Clone + venv
git clone https://github.com/UniF1o/uniflo-api.git
cd uniflo-api
python -m venv .venv

# Activate the venv:
#   Windows:   .venv\Scripts\activate
#   macOS/Lx:  source .venv/bin/activate

# 2. Install (dev deps include pytest + ruff)
pip install -r requirements-dev.txt

# 3. Configure
cp .env.example .env
# fill in DATABASE_URL, SUPABASE_*, WEBHOOK_SECRET, DELETE_WEBHOOK_SECRET, etc.

# 4. Run migrations
alembic upgrade head

# 5. (Optional) seed three SA universities
make seed     # or: python scripts/seed_universities.py

# 6. Serve
uvicorn app.main:app --reload
# OpenAPI UI: http://localhost:8000/docs
```

---

## Environment variables

All are loaded from `.env` via `pydantic-settings`. See [`.env.example`](.env.example).

| Variable                  | Purpose                                                     |
|---------------------------|-------------------------------------------------------------|
| `DATABASE_URL`            | Postgres URL (Supabase pooler).                             |
| `SUPABASE_URL`            | `https://<project>.supabase.co` -- used for JWKS + Storage. |
| `SUPABASE_ANON_KEY`       | Anon key for the Supabase Python client.                    |
| `SUPABASE_JWT_SECRET`     | Legacy; kept for completeness. JWTs are verified via JWKS.  |
| `SUPABASE_STORAGE_BUCKET` | Name of the private bucket (e.g. `documents`).              |
| `WEBHOOK_SECRET`          | Shared secret for `user-created` / `user-updated` webhooks. |
| `DELETE_WEBHOOK_SECRET`   | Separate secret for `user-deleted` (least privilege).       |
| `SENTRY_DSN`              | Optional. Empty = disabled.                                 |
| `ENVIRONMENT`             | `development` / `staging` / `production` (sent to Sentry).  |
| `CORS_ORIGINS`            | Comma-separated origin list. Defaults: localhost + Vercel.  |
| `FAKE_AUTOMATION`         | `true` until Phase 3 wires real Playwright adapters.        |

Phase 2+ keys (`ANTHROPIC_API_KEY`, `RESEND_API_KEY`) are placeholders in the
example file -- not consumed yet.

---

## Common commands

```bash
# Lint
ruff check .

# Tests (auto-discovers tests/ from pyproject.toml)
pytest -v

# Migrations
alembic current
alembic history
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1

# Generate frontend types from the live OpenAPI spec
npx openapi-typescript https://uniflo-api.onrender.com/openapi.json \
  -o lib/api/schema.d.ts
```

---

## Auth model

1. Frontend signs the user in with Supabase, gets an RS256/ES256 JWT.
2. Frontend sends `Authorization: Bearer <token>` on every protected request.
3. `AuthMiddleware` verifies the signature against the Supabase JWKS endpoint
   (`/auth/v1/.well-known/jwks.json`), then stores the decoded payload on
   `request.state.user`.
4. `ensure_user_synced(sub, email)` upserts a row into `public.users` so every
   authenticated request sees its mirror. Belt-and-suspenders for missed
   webhooks.
5. Public routes bypass auth: `/health`, `/ping`, `/openapi.json`, `/docs/*`,
   `/redoc/*`, `/universities/*`, and the three webhook endpoints (which have
   their own shared-secret check).

---

## Document storage

The `documents` bucket is **private**. The DB stores `storage_path`; the API
mints a fresh 1-hour signed URL on every read via
`supabase.storage.from_(bucket).create_signed_url(path, 3600)`. Uploaded paths
use a UUID, never the user-supplied filename, to avoid traversal + collision.

---

## Migrations

Linear chain (no branches):

```
cd25ac463c44  initial schema (profiles, documents, academic_records)
4dee565d63cb  add users + FK
7a1c2f4b9d10  documents: storage_url -> storage_path
1026b4a0314a  phase 2: universities, applications, application_jobs
5f641ecfb811  (empty no-op revision; applied to prod, kept for chain integrity)
a3b2c1d4e5f6  student_profiles: relax NOT NULLs for partial upsert
b4c3d2e1f0a9  academic_records: aggregate -> Float, UNIQUE(student_id)
```

`alembic upgrade head` is idempotent. `alembic/env.py` imports `app.models`, so
`--autogenerate` can see every table.

---

## Testing

```bash
pytest -v
```

Tests mock the database (`app.dependency_overrides[get_session] = lambda: mock_session`),
mock `jwt.decode` to bypass JWKS, and patch `ensure_user_synced` via an autouse
fixture in `tests/conftest.py`. **No real database is touched.** CI runs the
same suite plus `ruff check .` on every push and PR.

---

## Deployment

- Render Web Service (Docker-less; runs from the GitHub repo).
- CI workflow (`.github/workflows/backend.yml`) runs tests + lint on push and
  PR, then fires Render's deploy hook on `main`.
- Migrations are not auto-applied by CI. `alembic upgrade head` is run
  against the production database as part of the release (by a person, or
  via a Render shell). Revision `b4c3d2e1f0a9` has already been applied to
  production.

---

## License

Internal / unpublished. No license granted.
