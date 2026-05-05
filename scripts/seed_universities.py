import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_engine
from datetime import date
from sqlmodel import Session, select
from app.models import University

"""
Seed script — SA universities for Uniflo MVP

Run with:
    python scripts/seed_universities.py

Requires DATABASE_URL in your .env file.
Idempotent — safe to run multiple times, upserts by name.
"""

UNIVERSITIES = [
        {
            "name": "University of Cape Town",
            "website": "https://uct.ac.za",
            "portal_url": "https://publicaccess.uct.ac.za",
            "open_date": date(2026, 4, 1),
            "close_date": date(2026, 7, 31),
            "is_active": True
        },
        {
            "name": "University of the Witwatersrand",
            "website": "https://www.wits.ac.za",
            "portal_url": "https://self-service.wits.ac.za",
            "open_date": date(2026, 4, 1),
            "close_date": date(2026, 9, 30),
            "is_active": True
        },
        {
            "name": "University of Johannesburg",
            "website": "https://www.uj.ac.za",
            "portal_url": "https://registration.uj.ac.za",
            "open_date": date(2026, 4, 1),
            "close_date": date(2026, 10, 31),
            "is_active": True
        }
    ]

def seed():
    engine = get_engine()
    with Session(engine) as session:
        for uni_data in UNIVERSITIES:
            statement = select(University).where(University.name == uni_data["name"])
            existing_uni = session.exec(statement).first()
            if existing_uni:
                # Update existing record
                for key, value in uni_data.items():
                    setattr(existing_uni, key, value)
                print(f"Updated university: {existing_uni.name}")
            else:
                # Create new record
                new_uni = University(**uni_data)
                session.add(new_uni)
                print(f"Added university: {new_uni.name}")
        session.commit()

if __name__ == "__main__":
    seed()