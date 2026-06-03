import uuid
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ApplicationChoice(SQLModel, table=True):
    """One ordered programme choice within an application. Every target portal
    takes more than one choice (UJ 2, UCT 2, Wits 3, UP 2), so a single
    `applications.programme` string isn't enough. Choice 1 mirrors
    `applications.programme` (kept for back-compat); choices 2+ live only here.
    `eligible` carries the portal-computed eligibility (UP rejects ineligible
    at selection; UJ tags "ELIGIBLE TO APPLY-Y")."""

    __tablename__ = "application_choices"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "choice_number",
            name="uq_application_choices_application_choice",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(
        foreign_key="applications.id", nullable=False, index=True
    )
    choice_number: int = Field(nullable=False)
    programme: str = Field(nullable=False)
    eligible: Optional[bool] = Field(default=None, nullable=True)
