# Code Review — 2026-04-22

Full review against the Phase 1 spec ([Andziso Detailed Phase 1 Plan](https://www.notion.so/341930d2bab080ad8fc5db1f71a50133)). Below is every file that changed, grouped by category, with the reasoning behind each change.

All tests (`pytest`, 33 tests) pass. `ruff check .` is clean. `alembic history` loads with all four models registered.

---

## 1. Critical bugs

### `app/api/documents/service.py`
**Bug:** The service called `get_supabase.storage.from_(...)`. `get_supabase` is a factory function (`def get_supabase() -> Client`), not a client instance — every call to it would've raised `AttributeError: 'function' object has no attribute 'storage'` in production. CI didn't catch it because the test mocks mirrored the same bug (they patched `get_supabase` and then accessed `.storage` on the *patched function* rather than on its return value).

**Fix:** Every call site now uses `get_supabase().storage.from_(...)`. See the full rewrite below in §5 (private bucket / signed URLs) for the final form.

### `requirements.txt`
**Bug:** File was UTF-16 LE with a BOM and CRLF line endings. `pip install -r requirements.txt` on Linux (GitHub Actions runner) reads this as a pile of binary gibberish and fails parsing. Reproducible locally with `file requirements.txt` → `Unicode text, UTF-16, little-endian`.

**Fix:** Re-encoded to ASCII/UTF-8 with LF line endings. Added `email-validator==2.3.0` and `dnspython==2.8.0` (a transitive dependency of email-validator) — required by the new `pydantic.EmailStr` fields in `auth/schemas.py` and `webhooks/router.py`.

### `alembic/env.py`
**Bug:** Only imported `StudentProfile`, `AcademicRecord`, `Document`. `User` was absent, so Alembic's autogenerate was blind to it — which is exactly how the initial phase-1 migration ended up split into two (`cd25ac463c44` created everything except `users`; `4dee565d63cb` backfilled the `users` table afterwards). Any future `alembic revision --autogenerate` would have continued to drop `User`-related changes on the floor.

**Fix:** Import `User` alongside the others with a `# noqa: F401` to silence the unused-import lint (it's referenced by `SQLModel.metadata`, not by name). Ruff also re-sorted the imports to the standard ordering.

### Stray `git` file
**Bug:** An empty file named `git` sat at repo root — probably the residue of a broken shell redirect.

**Fix:** Deleted.

### No CORS middleware — `app/main.py`, `app/config.py`, `.env.example`
**Bug:** The Next.js frontend (Partner A) is explicitly designed to call these endpoints from the browser. Without `CORSMiddleware` the browser's preflight `OPTIONS` will fail and every cross-origin call gets blocked. This was a functional blocker for frontend integration.

**Fix:**
- `app/config.py`: new `CORS_ORIGINS: list[str]` setting with default `["http://localhost:3000"]`, plus a `field_validator` that splits comma-separated env values (Pydantic can't parse lists from dotenv strings by default).
- `app/main.py`: `CORSMiddleware` registered before `AuthMiddleware` (order matters — CORS preflight must not be subject to the JWT check).
- `.env.example`: documents `CORS_ORIGINS=http://localhost:3000` as the default.

---

## 2. Security fixes

### `app/api/webhooks/router.py` — constant-time secret compare + Pydantic validation
**Issues:**
1. `secret != settings.WEBHOOK_SECRET` is vulnerable to timing attacks. Use `hmac.compare_digest`.
2. The router read `request.json()` directly and indexed `payload["record"]["id"]` / `payload["record"]["email"]` with no schema — any malformed payload blew up with a raw KeyError and returned 500.
3. Commented-out dead code (`#user_created_at = record["created_at"]`).

**Fix:**
- Added `UserCreatedPayload`, `UserCreatedRecord`, `UserDeletedPayload`, `UserDeletedRecord` Pydantic models — FastAPI now auto-rejects malformed bodies with 422.
- Factored secret verification into `_verify_secret(provided, expected)` using `hmac.compare_digest`.
- Moved routes under a router with `prefix="/webhooks"` so the path strings in `@router.post` stay short (`/user-created`, `/user-deleted`). The external URLs remain identical: `/webhooks/user-created`, `/webhooks/user-deleted`.
- `x-webhook-secret` now declared as a FastAPI `Header` dependency rather than read from `request.headers`.
- Removed dead code.

### `app/api/documents/service.py` — path traversal + filename collisions
**Issues:**
1. Storage path was `{user_id}/{document_type}/{file.filename}`. If the user uploaded a file named `../../../secrets.pdf` the resulting path would attempt to traverse out of the user's prefix (Supabase Storage would typically normalise, but this is unnecessary risk to accept).
2. `upsert=true` combined with user-supplied filenames meant that uploading two different documents with the same filename would **silently overwrite each other** in storage, while the DB kept two records pointing at the same object.

**Fix:**
- Storage path is now `{user_id}/{document_type}/{document_uuid}{ext}`, where `document_uuid` is generated with `uuid.uuid4()` before the `Document` row is created, and `ext` is sanitised by `_safe_extension()` (lowercased, alphanumeric-only suffix).
- No part of the user-supplied filename ends up in the storage path any more.

### `app/api/middleware/auth.py` — safer path matching + token parsing
**Issues:**
1. `if request.url.path in PUBLIC_ROUTES` does an exact match. Swagger UI loads sub-resources under `/docs` (notably `/docs/oauth2-redirect` when OAuth is configured) and the redoc page serves assets under `/redoc/...`. These would have been blocked with 401 once anything beyond the bare `/docs` page was requested.
2. `auth_header.split(" ")[1]` silently succeeds if someone sends `Bearer   tok` (multiple spaces).

**Fix:**
- New `_is_public(path)` helper: exact-match set for `/health`, `/ping`, `/openapi.json`, and the two webhook routes; prefix-match tuple for `/docs`, `/redoc`. Prefix match checks `path == p or path.startswith(p + "/")` so `/docs-extra` wouldn't accidentally match.
- Token split uses `split(" ", 1)[1]` — collapses any internal whitespace robustly.

### `app/db.py` — connection pool health
**Issue:** Supabase's pooler drops idle connections aggressively. Without `pool_pre_ping` a request that picks up a stale connection returns a 500 to the user.

**Fix:** `create_engine(settings.DATABASE_URL, pool_pre_ping=True)`.

---

## 3. Type safety / schema correctness

### `app/api/auth/schemas.py`
- `UserResponse.id`: `str` → `uuid.UUID` (matches the DB column).
- `UserResponse.email`: `str` → `EmailStr` (validates format on every response).

### `app/api/profiles/schemas.py`
- `StudentProfileResponse.gender`: `str` → `GenderEnum`.
- `StudentProfileResponse.home_language`: `str` → `HomeLanguageEnum`.

  The DB stores raw strings, so if a future migration drifts the enum, a mismatched DB value is now a 500 at response serialisation rather than a silently-wrong value being returned to the client.

### `app/api/documents/schemas.py`
- `DocumentResponse.type`: `str` → `DocumentType` enum.
- `DocumentResponse.storage_url` stays as a free-form `str` — it holds a signed URL whose shape isn't worth modelling.

### `app/api/auth/router.py`
- `user_id` from the JWT is now parsed through `uuid.UUID(...)` before being passed to `session.get(User, ...)`. SQLAlchemy will coerce either way, but this makes the intent explicit and fails fast if the `sub` claim is ever malformed.

### `app/config.py`
- `SENTRY_DSN`: bare `str = ""` default → `Optional[str] = None`. Tests pass an empty string and the truthiness check still works.

### Models — timezone awareness and cleanup
- `app/models/user.py`: `created_at` now uses `DateTime(timezone=True)` at the column level (was naive `DateTime`). Matches `StudentProfile.updated_at`.
- `app/models/document.py`: `uploaded_at` same treatment; `storage_url` replaced by `storage_path` (see §5).
- All models: unused imports pruned (e.g. `timezone`, `date`, `Optional`) and imports sorted by ruff.

---

## 4. Polish & project hygiene

### `app/main.py`
- `CORSMiddleware` registered before `AuthMiddleware` so preflight `OPTIONS` requests aren't blocked by the JWT check.
- `/ping` response body simplified (`{"status": "ok"}` — HEAD responses can't carry a body anyway; FastAPI strips it).
- Removed redundant trailing comments.

### `app/api/webhooks/router.py`
Routes now attached to `APIRouter(prefix="/webhooks", tags=["webhooks"])` so path strings are shorter and the OpenAPI doc groups them under a `webhooks` tag.

### `.env.example`
Before: typos (`secert`), inconsistent spacing (`WEBHOOK_SECRET =`), uncommented future-phase variables polluting the file.

After: grouped into sections (Database / Supabase / Observability / CORS / Phase 2+), no typos, clear labels. `CORS_ORIGINS` documented. `ANTHROPIC_API_KEY` / `RESEND_API_KEY` moved under a "Phase 2+ integrations (unused in Phase 1)" comment so the team knows what's live vs. aspirational.

### `pyproject.toml`
- Ruff config moved from the deprecated top-level `select` to `[tool.ruff.lint]` (ruff 0.15 warns about the old form).
- `lint.ignore = ["E501"]` — line length is a formatter concern (black), not a linter one. Kept E/F/I for actual errors.
- `extend-exclude = ["alembic/versions"]` — autogenerated migrations shouldn't be linted.

### `.github/workflows/backend.yml`
Before:
- Ran `pytest tests/test_*.py -v` seven times (once per file) — slow and obscured the real test count.
- `actions/checkout@v3` and `actions/setup-python@v4` were two majors behind.
- No linting step.
- Deploy fired on any `push`, including to non-main branches.
- Triggered only on `push`, never on `pull_request` — so PRs showed no CI status until merged.

After:
- Single `pytest -v` invocation (reads `testpaths` from `pyproject.toml`).
- Added `ruff check .` before tests.
- Bumped to `actions/checkout@v4`, `actions/setup-python@v5` with `cache: pip` for faster installs.
- Triggers on `push` **and** `pull_request`.
- Deploy gated on `github.ref == 'refs/heads/main' && github.event_name == 'push'` so PR runs don't hit the Render deploy hook.
- `curl -fsS` so a deploy-hook failure surfaces instead of silently swallowing errors.

### `.gitignore`
Added `.claude/settings.local.json` — per-user Claude Code permissions file. The shared `.claude/settings.json` (if ever added) should still be committed.

### Ruff auto-fixes
Imports re-sorted across nearly every Python file in the repo (`I001` rule). These are mechanical reorderings only.

---

## 5. Documents: private bucket + signed URLs

This was the largest semantic change. Per the Phase 1 spec, the `documents` bucket is **private** — files should only be accessible by the student who owns them. The original code stored the return value of `get_public_url()`, which isn't retrievable for a private bucket.

### Approach
- Store the **storage path** on the `Document` row, not a URL.
- Generate a fresh, short-lived signed URL (1-hour TTL) at read time via `supabase.storage.from_(bucket).create_signed_url(path, 3600)`.
- Frontend contract is unchanged: the `DocumentResponse.storage_url` field still exists and still contains a browser-usable URL; it's just a new signed URL each call.

### Files touched

**`app/models/document.py`**: `storage_url: str` column → `storage_path: str`. Same NULL/NOT NULL semantics.

**`alembic/versions/7a1c2f4b9d10_documents_storage_path.py`** *(new)*: the migration.
- `down_revision` chained onto `4dee565d63cb` so the existing history is preserved.
- `upgrade()`: adds `storage_path` with a temporary `server_default=""` (so any pre-existing rows don't violate NOT NULL), clears the default, then drops `storage_url`.
- `downgrade()` reverses the operation.

**To apply:** `alembic upgrade head`. If there are existing rows pointing at the old column, you'll need to either wipe them (Phase 1 pre-prod, probably fine) or backfill `storage_path` manually before the `drop_column` — the migration as written will leave empty strings for existing rows.

**`app/api/documents/service.py`** (full rewrite):
- New helper `_create_signed_url(storage_path) -> str` — calls `create_signed_url`, reads `signedURL` / `signedUrl` / `signed_url` from the response (the storage3 library has spelled this key differently across versions, so read defensively).
- New helper `_to_response(document) -> DocumentResponse` — assembles the response with a fresh signed URL and casts `type` to the `DocumentType` enum.
- `upload_document` now returns `DocumentResponse` (not the bare `Document`) since the signed URL isn't an attribute of the model.
- `get_documents` returns `list[DocumentResponse]`.
- `delete_document` uses `document.storage_path` directly — no more URL parsing via `urlparse` to figure out the filename. This was fragile (query-string handling, double slashes, etc.) and is now gone.
- `SIGNED_URL_TTL_SECONDS = 60 * 60` — constant at module scope so it's easy to find and tune.

**`tests/test_documents_endpoints.py`**:
- Helper `_wire_storage_mocks(mock_get_supabase)` centralises the mock setup: `upload`, `remove`, and `create_signed_url` all return canned values.
- `make_mock_document()` now sets `storage_path` instead of `storage_url`.
- Two new assertions:
  - On successful upload: `response.json()["storage_url"] == SIGNED_URL` (proves the fresh signed URL reaches the client).
  - On successful delete: `bucket.remove.assert_called_once()` + `call_args[0][0] == [expected_path]` (proves the path sent to storage matches what we stored).

---

## 6. Items reviewed but intentionally left alone

### Migration history squash
The two phase-1 migrations (`cd25ac463c44` + `4dee565d63cb`) could be combined into one now that Alembic can see all four models. But since those migrations are already applied to the live Supabase database, squashing them would mean rewriting applied history — high risk, low reward. The history as it stands is messy but correct.

### Private bucket RLS
The code now uses signed URLs, which is the right approach for a private bucket. The complementary piece — Supabase RLS policies on the `documents` bucket restricting each user's prefix — needs to be configured in the Supabase dashboard, not in this repo. Outside scope.

### `DELETE /documents/{id}` returning 200 instead of 204
Pure convention — 204 (No Content) is more idiomatic for DELETE, but 200 with `{"status": "ok"}` is the existing contract and the frontend may already rely on parsing the body. Not changed.

### Backfill strategy for `storage_path`
The new migration sets an empty `server_default` for existing rows and then drops it. If you have real documents in the DB already, you'll want to backfill `storage_path` for them before running the migration (or run a data migration that parses the old `storage_url` values). For Phase 1 pre-production, this is probably moot.

---

## 7. Quick verification commands

```bash
# From repo root, with a venv activated:
pip install -r requirements.txt
ruff check .
pytest -v

# Inspect migration chain:
alembic history

# Apply the new migration:
alembic upgrade head
```

Test run on my side: **33 passed in ~2s**, `ruff check .` — **All checks passed!**
