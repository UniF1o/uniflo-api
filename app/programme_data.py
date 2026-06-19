"""Prospectus data freshness checks.

Each ``data/programmes/<uni>.json`` is transcribed from one university's
prospectus for one intake year (its top-level ``intake_year``). This module
compares that year against the active application cycle (:func:`active_intake_year`)
so we never silently run the recommendation engine on a prospectus that no longer
matches the year students are applying for — a stale file makes the engine return
empty/wrong results without erroring.

Pure logic, no DB. Driven by :mod:`scripts.check_prospectus_year` (the CLI
pipeline), the seed script's guard, and the freshness tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.intake import active_intake_year

# data/programmes/ relative to the repo root (this file lives at app/programme_data.py).
PROGRAMMES_DIR = Path(__file__).resolve().parent.parent / "data" / "programmes"

# Freshness classifications.
CURRENT = "current"  # file targets the active cycle — good
STALE = "stale"  # file is behind the active cycle — DANGER, needs re-transcribing
AHEAD = "ahead"  # file targets a future cycle — fine, loaded early


@dataclass
class FreshnessReport:
    """The result of checking one prospectus data file."""

    path: Path
    intake_year: Optional[int]
    active_year: int
    status: str
    message: str

    @property
    def is_stale(self) -> bool:
        return self.status == STALE

    @property
    def ok(self) -> bool:
        # "ahead" is acceptable (data loaded before the cycle catches up);
        # only "stale" is a failure.
        return self.status in (CURRENT, AHEAD)


def assess(file_intake_year: Optional[int], active_year: int) -> tuple[str, str]:
    """Classify a file's ``intake_year`` against the active cycle.

    Returns a ``(status, human_message)`` pair.
    """
    if file_intake_year is None:
        return (
            STALE,
            "missing top-level 'intake_year' — cannot confirm the data matches "
            f"the active {active_year} application cycle",
        )
    if file_intake_year == active_year:
        return (
            CURRENT,
            f"intake_year {file_intake_year} matches the active application cycle",
        )
    if file_intake_year < active_year:
        return (
            STALE,
            f"intake_year {file_intake_year} is behind the active {active_year} "
            "cycle — re-transcribe from the latest prospectus and re-seed",
        )
    return (
        AHEAD,
        f"intake_year {file_intake_year} is ahead of the active {active_year} "
        "cycle — loaded early, will surface once the cycle catches up",
    )


def _load_intake_year(path: Path) -> Optional[int]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("intake_year")


def check_file(path: Path, active_year: Optional[int] = None) -> FreshnessReport:
    """Build a :class:`FreshnessReport` for a single data file."""
    year = active_year if active_year is not None else active_intake_year()
    file_year = _load_intake_year(path)
    status, message = assess(file_year, year)
    return FreshnessReport(
        path=path,
        intake_year=file_year,
        active_year=year,
        status=status,
        message=message,
    )


def check_all(active_year: Optional[int] = None) -> list[FreshnessReport]:
    """Check every ``*.json`` under ``data/programmes/``.

    Returns reports sorted by filename. An empty directory yields an empty list
    (the caller decides whether that is itself a problem).
    """
    year = active_year if active_year is not None else active_intake_year()
    if not PROGRAMMES_DIR.is_dir():
        return []
    return [check_file(p, year) for p in sorted(PROGRAMMES_DIR.glob("*.json"))]
