"""
Seed university programme admission requirements from data/programmes/<uni>.json.

Upserts faculties and programmes into the DB and sets the university's
scoring_method. Idempotent — safe to run multiple times; upserts on
(university_id, qualification_code, intake_year), falling back to (name, intake_year).

Refuses to seed a prospectus whose intake_year is behind the active application
cycle (stale data → wrong/empty recommendations). Pass --allow-stale to override
for a deliberate backfill.

Run with:
    python scripts/seed_programmes.py up.json
    python scripts/seed_programmes.py uj.json
    python scripts/seed_programmes.py           # seeds every registered file
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select

from app.db import get_engine
from app.intake import active_intake_year
from app.models import Faculty, Programme, University
from app.programme_data import assess

PROGRAMMES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "programmes",
)

# Each data file is bound to one university name (resolved in the DB) and the
# APS scoring_method to apply. Add a row here when transcribing a new university.
REGISTRY: dict[str, dict[str, str]] = {
    "up.json": {"university": "University of Pretoria", "scoring_method": "up_aps"},
    "uj.json": {"university": "University of Johannesburg", "scoring_method": "up_aps"},
}


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s)


def seed_file(filename: str, allow_stale: bool = False) -> None:
    key = os.path.basename(filename)
    entry = REGISTRY.get(key)
    if entry is None:
        print(f"ERROR: '{key}' is not registered in seed_programmes.REGISTRY.")
        sys.exit(1)
    university_name = entry["university"]
    scoring_method = entry["scoring_method"]

    path = os.path.join(PROGRAMMES_DIR, key)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    intake_year: int = data["intake_year"]
    default_close: date | None = _parse_date(data.get("default_close_date"))
    faculty_overrides: dict = data.get("faculty_overrides", {})
    programmes_data: list[dict] = data["programmes"]

    active_year = active_intake_year()
    status, message = assess(intake_year, active_year)
    print(f"\n=== {key} → {university_name} ===")
    print(f"Freshness check: {message}")
    if status == "stale":
        if not allow_stale:
            print(
                "ABORTED: refusing to seed stale prospectus data. "
                "Re-transcribe from the latest prospectus, or pass --allow-stale "
                "to seed it anyway (deliberate backfill)."
            )
            sys.exit(1)
        print("WARNING: seeding stale data because --allow-stale was passed.")

    engine = get_engine()
    with Session(engine) as session:
        uni = session.exec(
            select(University).where(University.name == university_name)
        ).first()
        if not uni:
            print(f"ERROR: university '{university_name}' not found — run seed_universities.py first")
            sys.exit(1)

        uni.scoring_method = scoring_method
        session.add(uni)
        print(f"Set {university_name}.scoring_method = '{scoring_method}'")

        faculty_cache: dict[str, Faculty] = {}

        for prog_data in programmes_data:
            faculty_name: str = prog_data["faculty"]

            if faculty_name not in faculty_cache:
                existing_faculty = session.exec(
                    select(Faculty).where(
                        Faculty.university_id == uni.id,
                        Faculty.name == faculty_name,
                    )
                ).first()

                override = faculty_overrides.get(faculty_name, {})
                close_date = _parse_date(override.get("close_date")) or default_close

                if existing_faculty:
                    existing_faculty.close_date = close_date
                    faculty_cache[faculty_name] = existing_faculty
                    print(f"  Faculty exists: {faculty_name}")
                else:
                    new_faculty = Faculty(
                        university_id=uni.id,
                        name=faculty_name,
                        close_date=close_date,
                    )
                    session.add(new_faculty)
                    session.flush()
                    faculty_cache[faculty_name] = new_faculty
                    print(f"  Created faculty: {faculty_name}")

            faculty = faculty_cache[faculty_name]

            qual_code: str | None = prog_data.get("qualification_code")
            prog_name: str = prog_data["name"]

            existing_prog = None
            if qual_code:
                existing_prog = session.exec(
                    select(Programme).where(
                        Programme.university_id == uni.id,
                        Programme.qualification_code == qual_code,
                        Programme.intake_year == intake_year,
                    )
                ).first()

            if existing_prog is None:
                existing_prog = session.exec(
                    select(Programme).where(
                        Programme.university_id == uni.id,
                        Programme.name == prog_name,
                        Programme.intake_year == intake_year,
                    )
                ).first()

            now = datetime.now(timezone.utc)

            if existing_prog:
                existing_prog.faculty_id = faculty.id
                existing_prog.name = prog_name
                existing_prog.qualification_code = qual_code
                existing_prog.min_aps = prog_data.get("min_aps")
                existing_prog.requirements = prog_data.get("requirements", {})
                existing_prog.notes = prog_data.get("notes")
                existing_prog.is_active = prog_data.get("is_active", False)
                existing_prog.source_page = prog_data.get("source_page")
                existing_prog.updated_at = now
                print(f"    Updated: {prog_name}")
            else:
                new_prog = Programme(
                    university_id=uni.id,
                    faculty_id=faculty.id,
                    name=prog_name,
                    qualification_code=qual_code,
                    intake_year=intake_year,
                    min_aps=prog_data.get("min_aps"),
                    requirements=prog_data.get("requirements", {}),
                    notes=prog_data.get("notes"),
                    is_active=prog_data.get("is_active", False),
                    source_page=prog_data.get("source_page"),
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_prog)
                print(f"    Created: {prog_name}")

        session.commit()
        print(f"Done — {len(programmes_data)} programmes processed for {university_name} intake {intake_year}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed university programme admission requirements."
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="data/programmes file to seed (e.g. up.json, uj.json). Omit to seed all registered files.",
    )
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="seed even if the prospectus intake_year is behind the active cycle",
    )
    args = parser.parse_args()

    targets = [args.file] if args.file else list(REGISTRY)
    for target in targets:
        seed_file(target, allow_stale=args.allow_stale)
