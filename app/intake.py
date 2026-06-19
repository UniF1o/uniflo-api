"""The active application/intake cycle.

Single source of truth for "which intake year are we dealing with right now".
Both the recommendation engine (which programmes to surface) and the prospectus
freshness pipeline (whether the seeded data still matches the live cycle) key off
this, so it must be defined in exactly one place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def active_intake_year(now: Optional[datetime] = None) -> int:
    """Return the intake year the current application cycle targets.

    South African undergraduate applications run April–June each year for the
    *following* year's intake, so the active cycle is always the current
    calendar year + 1. ``now`` is injectable so callers (and tests) can pin the
    reference instant.
    """
    now = now or datetime.now(timezone.utc)
    return now.year + 1
