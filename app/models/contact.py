import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


class Contact(SQLModel, table=True):
    """A person attached to a student's application: next of kin, fee payer,
    parent/guardian, or emergency contact. Portals (UJ, Wits, UCT) require one
    or more of these, with their own name/contact/address. At most one contact
    per type per student (upsert semantics, like academic_records)."""

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
