"""Prospectus freshness pipeline.

Checks every data/programmes/*.json against the active application cycle and
fails (exit 1) if any file's intake_year is behind it — i.e. the seeded
prospectus no longer matches the year students are applying for. Run locally or
in CI:

    python scripts/check_prospectus_year.py

Exit codes:
    0  all files current or loaded ahead of the cycle
    1  at least one file is stale (or no data files found)
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.intake import active_intake_year
from app.programme_data import PROGRAMMES_DIR, check_all


def main() -> int:
    active_year = active_intake_year()
    reports = check_all(active_year)

    print(f"Active application cycle: {active_year} intake")
    print(f"Data directory: {PROGRAMMES_DIR}\n")

    if not reports:
        print("ERROR: no programme data files found — nothing to seed or match.")
        return 1

    stale = []
    for report in reports:
        marker = {"current": "OK  ", "ahead": "AHEAD", "stale": "STALE"}.get(
            report.status, "?"
        )
        print(f"[{marker}] {report.path.name}: {report.message}")
        if report.is_stale:
            stale.append(report)

    if stale:
        names = ", ".join(r.path.name for r in stale)
        print(
            f"\nFAILED: {len(stale)} stale prospectus file(s): {names}\n"
            "Re-transcribe from the latest prospectus, bump 'intake_year', and re-seed."
        )
        return 1

    print("\nAll prospectus data matches the active application cycle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
