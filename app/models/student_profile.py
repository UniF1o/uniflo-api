import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class StudentProfile(SQLModel, table=True):
    __tablename__ = "student_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, unique=True, index=True
    )
    title: Optional[str] = Field(default=None, nullable=True)
    first_name: Optional[str] = Field(default=None, nullable=True)
    middle_names: Optional[str] = Field(default=None, nullable=True)
    last_name: Optional[str] = Field(default=None, nullable=True)
    maiden_name: Optional[str] = Field(default=None, nullable=True)
    preferred_name: Optional[str] = Field(default=None, nullable=True)
    id_number: Optional[str] = Field(default=None, unique=True, nullable=True)
    date_of_birth: Optional[date] = Field(default=None, nullable=True)
    phone: Optional[str] = Field(default=None, nullable=True)
    # Residential / home address.
    street_address: Optional[str] = Field(default=None, nullable=True)
    suburb: Optional[str] = Field(default=None, nullable=True)
    city: Optional[str] = Field(default=None, nullable=True)
    province: Optional[str] = Field(default=None, nullable=True)
    postal_code: Optional[str] = Field(default=None, sa_column=Column(String(4), nullable=True))
    # Postal / mailing address — used by portals that offer a "postal differs
    # from home" option (UJ, UCT, Wits). Defaults to "same as residential".
    mailing_same_as_residential: Optional[bool] = Field(default=None, nullable=True)
    mailing_street_address: Optional[str] = Field(default=None, nullable=True)
    mailing_suburb: Optional[str] = Field(default=None, nullable=True)
    mailing_city: Optional[str] = Field(default=None, nullable=True)
    mailing_province: Optional[str] = Field(default=None, nullable=True)
    mailing_postal_code: Optional[str] = Field(default=None, sa_column=Column(String(4), nullable=True))
    nationality: Optional[str] = Field(default=None, nullable=True)
    is_sa_citizen: Optional[bool] = Field(default=None, nullable=True)
    # Full residency taxonomy — for non-SA-citizen applicants the portals swap
    # the SA-ID field for a passport + permit block (UJ oapCitizenType=No, UCT
    # Step-2 citizenship swap, Wits nationality-driven ID type).
    citizenship_status: Optional[str] = Field(default=None, nullable=True)
    passport_number: Optional[str] = Field(default=None, nullable=True)
    study_permit_type: Optional[str] = Field(default=None, nullable=True)
    gender: Optional[str] = Field(default=None, nullable=True)
    home_language: Optional[str] = Field(default=None, nullable=True)
    religion: Optional[str] = Field(default=None, nullable=True)
    disability: Optional[str] = Field(default=None, nullable=True)
    # Free-text detail + required-assistance description (UP/Wits/UCT capture
    # more than the single disability category).
    disability_detail: Optional[str] = Field(default=None, nullable=True)
    disability_assistance: Optional[str] = Field(default=None, nullable=True)
    marital_status: Optional[str] = Field(default=None, nullable=True)
    ethnicity: Optional[str] = Field(default=None, nullable=True)
    # Schooling / activity.
    current_activity: Optional[str] = Field(default=None, nullable=True)
    exam_number: Optional[str] = Field(default=None, nullable=True)
    sport: Optional[str] = Field(default=None, nullable=True)
    # Chosen FET subject names (no marks) — captured in setup for Grade 10/11
    # learners who have picked subjects but have no results yet. Feeds careers
    # subject-matching before an AcademicRecord (with marks) exists.
    subject_choices: Optional[Any] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    # Residence + funding intent (relayed to portals; not auto-actioned).
    wants_residence: Optional[bool] = Field(default=None, nullable=True)
    preferred_residence: Optional[str] = Field(default=None, nullable=True)
    applying_nsfas: Optional[bool] = Field(default=None, nullable=True)
    applying_institutional_funding: Optional[bool] = Field(default=None, nullable=True)
    # NBT (UCT) — student writes it on the separate NBT portal; we only capture.
    nbt_reference: Optional[str] = Field(default=None, nullable=True)
    nbt_year: Optional[int] = Field(default=None, nullable=True)
    nbt_date: Optional[date] = Field(default=None, nullable=True)
    # UCT-only redress / disadvantage-factor answers (parents' apartheid
    # classification, parents'/grandparents' education, child-support grant,
    # social pension, mother's first language). UCT-specific + sensitive, so
    # kept as a namespaced JSON blob rather than columns on the core profile.
    redress_factors: Optional[Any] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    # Guardian consent (POPIA) — required before processing a minor's (<18)
    # personal data. Details of the guardian live in the `contacts` table
    # (type=guardian); these record that consent was given, by whom, and when.
    guardian_consent_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    guardian_consent_by: Optional[str] = Field(default=None, nullable=True)
    guardian_relationship: Optional[str] = Field(default=None, nullable=True)
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
