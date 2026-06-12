import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


class Contact(SQLModel, table=True):
    """A person attached to a student's application: next of kin, fee payer,
    parent/guardian, or emergency contact. At most one contact per type per
    student (upsert semantics, like academic_records).

    Cross-portal finding (all four portals live-verified, 2026-06-12): ONE
    captured adult contact satisfies every portal — UP asks for nobody; UJ's
    next of kin + account contact may be the same person; UCT collapses
    parent/guardian + fee payer via a checkbox; Wits' emergency contact has a
    "same as next of kin" toggle. The automation mapping resolves each portal
    role through fallback chains across types, so capture ONE parent/guardian
    (as `guardian` or `next_of_kin`) and add a `fee_payer` row only when the
    payer genuinely differs. The `emergency` type exists only as an override —
    no portal requires it as a distinct person."""

    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "contact_type",
            name="uq_contacts_student_contact_type",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(
        foreign_key="student_profiles.id", nullable=False, index=True
    )
    # next_of_kin | fee_payer | guardian | emergency
    contact_type: str = Field(nullable=False)
    title: Optional[str] = Field(default=None, nullable=True)
    first_name: Optional[str] = Field(default=None, nullable=True)
    last_name: Optional[str] = Field(default=None, nullable=True)
    relationship: Optional[str] = Field(default=None, nullable=True)
    id_number: Optional[str] = Field(default=None, nullable=True)
    email: Optional[str] = Field(default=None, nullable=True)
    phone: Optional[str] = Field(default=None, nullable=True)
    street_address: Optional[str] = Field(default=None, nullable=True)
    suburb: Optional[str] = Field(default=None, nullable=True)
    city: Optional[str] = Field(default=None, nullable=True)
    province: Optional[str] = Field(default=None, nullable=True)
    postal_code: Optional[str] = Field(default=None, nullable=True)
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
