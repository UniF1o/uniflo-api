"""
Seed careers catalogue from data/careers/*.json.

Upserts careers into the `careers` table on `slug` (idempotent — safe to run
multiple times). Unlike seed_programmes.py, careers are not intake-year bound
so there is no stale-check or --allow-stale flag.

Run with:
    python scripts/seed_careers.py                 # seeds all industry files
    python scripts/seed_careers.py engineering.json   # seeds one file
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select

from app.db import get_engine
from app.models.career import Career

CAREERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "careers",
)

INDUSTRY_FILES = [
    "engineering.json",
    "ict.json",
    "health.json",
    "finance.json",
    "law.json",
    "natural_sciences.json",
    "agriculture.json",
    "education_social.json",
    "creative_media.json",
    "commerce_tourism.json",
    "skilled_trades.json",
]


def seed_file(filename: str) -> None:
    path = os.path.join(CAREERS_DIR, filename)
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    print(f"\n=== {filename} ({len(records)} careers) ===")
    engine = get_engine()
    created = updated = 0

    with Session(engine) as session:
        for data in records:
            slug = data["slug"]
            existing = session.exec(
                select(Career).where(Career.slug == slug)
            ).first()

            now = datetime.now(timezone.utc)

            if existing:
                existing.title = data["title"]
                existing.industry = data["industry"]
                existing.description = data["description"]
                existing.compensation = data["compensation"]
                existing.employability = data["employability"]
                existing.subject_rule = data["subject_rule"]
                existing.recommended_subjects = data.get("recommended_subjects")
                existing.programme_keywords = data["programme_keywords"]
                existing.is_active = data.get("is_active", True)
                existing.updated_at = now
                session.add(existing)
                print(f"  Updated: {slug}")
                updated += 1
            else:
                career = Career(
                    slug=slug,
                    title=data["title"],
                    industry=data["industry"],
                    description=data["description"],
                    compensation=data["compensation"],
                    employability=data["employability"],
                    subject_rule=data["subject_rule"],
                    recommended_subjects=data.get("recommended_subjects"),
                    programme_keywords=data["programme_keywords"],
                    is_active=data.get("is_active", True),
                    created_at=now,
                    updated_at=now,
                )
                session.add(career)
                print(f"  Created: {slug}")
                created += 1

        session.commit()
    print(f"Done — {created} created, {updated} updated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed careers catalogue.")
    parser.add_argument(
        "file",
        nargs="?",
        help="Industry file to seed (e.g. engineering.json). Omit to seed all.",
    )
    args = parser.parse_args()

    targets = [args.file] if args.file else INDUSTRY_FILES
    for target in targets:
        seed_file(target)
