"""Screenshot upload + signed-URL helpers (app.automation.screenshots).
Supabase Storage is mocked — no network."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import app.automation.screenshots as sc


def _shot(name, data=b"\x89PNG-fake"):
    return SimpleNamespace(name=name, data=data)


def test_is_storage_path():
    assert sc.is_storage_path("automation/a/b/00-login.png")
    assert not sc.is_storage_path("https://signed.example/x?token=abc")
    assert not sc.is_storage_path("")
    assert not sc.is_storage_path(None)


def test_upload_screenshots_returns_primary_path():
    app_id, job_id = uuid4(), uuid4()
    bucket = MagicMock()
    with patch.object(sc, "get_supabase") as gs:
        gs.return_value.storage.from_.return_value = bucket
        primary = sc.upload_screenshots(
            app_id, job_id, [_shot("login"), _shot("fill_form"), _shot("submit__failed")]
        )
    # primary == the last (final/failure) screenshot's path
    assert primary == f"automation/{app_id}/{job_id}/02-submit__failed.png"
    assert bucket.upload.call_count == 3


def test_upload_screenshots_empty_returns_none():
    assert sc.upload_screenshots(uuid4(), uuid4(), []) is None
    assert sc.upload_screenshots(uuid4(), uuid4(), None) is None


def test_upload_screenshots_survives_upload_error():
    bucket = MagicMock()
    bucket.upload.side_effect = [None, RuntimeError("storage down")]
    with patch.object(sc, "get_supabase") as gs:
        gs.return_value.storage.from_.return_value = bucket
        primary = sc.upload_screenshots(
            uuid4(), uuid4(), [_shot("login"), _shot("fill_form")]
        )
    # 1st uploaded, 2nd failed → primary is the 1st (never raises)
    assert primary.endswith("00-login.png")


def test_create_signed_url_reads_key_variants():
    bucket = MagicMock()
    bucket.create_signed_url.return_value = {"signedURL": "https://x/y?token=abc"}
    with patch.object(sc, "get_supabase") as gs:
        gs.return_value.storage.from_.return_value = bucket
        assert sc.create_signed_url("automation/a/b/00.png") == "https://x/y?token=abc"


def test_create_signed_url_handles_failure():
    with patch.object(sc, "get_supabase", side_effect=RuntimeError("down")):
        assert sc.create_signed_url("automation/a/b/00.png") == ""
