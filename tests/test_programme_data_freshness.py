"""Tests for the prospectus freshness pipeline.

Deterministic unit tests for the pure logic (active-cycle computation and the
stale/current/ahead classifier), plus a live tripwire asserting the shipped
data/programmes/*.json files still match the active application cycle — this one
fails CI when a new cycle starts and the prospectus data has not been refreshed.
"""

from datetime import datetime, timezone

from app.intake import active_intake_year
from app.programme_data import (
    AHEAD,
    CURRENT,
    STALE,
    assess,
    check_all,
)

# ---------------------------------------------------------------------------
# active_intake_year — the cycle always targets next calendar year
# ---------------------------------------------------------------------------


def test_active_intake_year_is_next_calendar_year():
    pinned = datetime(2026, 6, 18, tzinfo=timezone.utc)
    assert active_intake_year(pinned) == 2027


def test_active_intake_year_rolls_with_calendar_year():
    assert active_intake_year(datetime(2027, 1, 1, tzinfo=timezone.utc)) == 2028
    assert active_intake_year(datetime(2025, 12, 31, tzinfo=timezone.utc)) == 2026


def test_active_intake_year_defaults_to_now():
    # No reference instant -> uses the real clock; just assert it's sane.
    assert active_intake_year() == datetime.now(timezone.utc).year + 1


# ---------------------------------------------------------------------------
# assess — classify a file's intake_year against the active cycle
# ---------------------------------------------------------------------------


def test_assess_current_when_years_match():
    status, message = assess(2027, 2027)
    assert status == CURRENT
    assert "2027" in message


def test_assess_stale_when_file_behind_cycle():
    status, message = assess(2026, 2027)
    assert status == STALE
    assert "behind" in message


def test_assess_ahead_when_file_beyond_cycle():
    status, message = assess(2028, 2027)
    assert status == AHEAD
    assert "ahead" in message


def test_assess_stale_when_intake_year_missing():
    status, message = assess(None, 2027)
    assert status == STALE
    assert "intake_year" in message


# ---------------------------------------------------------------------------
# check_all — reports over the real data directory
# ---------------------------------------------------------------------------


def test_check_all_reports_carry_active_year_and_status():
    reports = check_all(active_year=2027)
    # The repo ships at least up.json.
    assert reports, "expected at least one data/programmes/*.json file"
    for report in reports:
        assert report.active_year == 2027
        assert report.status in (CURRENT, STALE, AHEAD)


def test_up_json_present_and_current_for_its_year():
    reports = check_all(active_year=2027)
    up = next((r for r in reports if r.path.name == "up.json"), None)
    assert up is not None, "up.json should be present in data/programmes/"
    assert up.intake_year == 2027
    assert up.status == CURRENT


# ---------------------------------------------------------------------------
# Live tripwire — shipped data must match the *real* active cycle.
# Fails CI when the application cycle rolls over and the prospectus data has not
# been re-transcribed/re-seeded. The fix is data, not code: update the JSON's
# intake_year from the latest prospectus and re-seed.
# ---------------------------------------------------------------------------


def test_shipped_prospectus_data_is_not_stale():
    stale = [r for r in check_all() if r.is_stale]
    assert not stale, (
        "Stale prospectus data for the active "
        f"{active_intake_year()} cycle: {[r.path.name for r in stale]}. "
        "Re-transcribe from the latest prospectus, bump 'intake_year', and re-seed."
    )
