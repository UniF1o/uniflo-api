"""Upload automation run screenshots to Storage + sign them for the dashboard.

The runtime captures a PNG after each step (`SubmissionResult.screenshots`).
Screenshots show the *filled application form* — i.e. the student's PII — so they
go to the same **private** bucket as documents and are read via short-lived signed
URLs (never public). We persist the storage **path** in
`application_jobs.screenshot_url` and mint a signed URL on read (see the
applications service), exactly like documents store `storage_path`.
"""

import logging
import re
from uuid import UUID

from app.config import settings
from app.supabase_client import get_supabase

logger = logging.getLogger(__name__)

SIGNED_URL_TTL_SECONDS = 60 * 60  # 1 hour
_PREFIX = "automation"


def _safe(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name or "")[:40] or "step"


def is_storage_path(value: str | None) -> bool:
    """True for a stored object path (vs an already-signed http(s) URL)."""
    return bool(value) and not value.startswith("http")


def upload_screenshots(application_id: UUID, job_id, screenshots) -> str | None:
    """Upload each step PNG under `automation/<application_id>/<job_id>/NN-step.png`
    and return the storage **path** of the primary (last) screenshot — the final
    or failure state — for `application_jobs.screenshot_url`. Best-effort: a
    capture/upload failure is logged, never raised (it must not sink the run)."""
    primary: str | None = None
    for i, shot in enumerate(screenshots or []):
        path = f"{_PREFIX}/{application_id}/{job_id}/{i:02d}-{_safe(shot.name)}.png"
        try:
            get_supabase().storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                path=path,
                file=shot.data,
                file_options={"content-type": "image/png", "upsert": "true"},
            )
            primary = path
        except Exception:  # noqa: BLE001
            logger.exception("screenshot upload failed for %s", path)
    return primary


def create_signed_url(storage_path: str) -> str:
    """Short-lived signed URL for a private-bucket screenshot, or '' on failure."""
    try:
        result = (
            get_supabase()
            .storage.from_(settings.SUPABASE_STORAGE_BUCKET)
            .create_signed_url(storage_path, SIGNED_URL_TTL_SECONDS)
        )
    except Exception:  # noqa: BLE001
        logger.exception("screenshot signed URL failed for %s", storage_path)
        return ""
    return (
        result.get("signedURL")
        or result.get("signedUrl")
        or result.get("signed_url")
        or ""
    )
