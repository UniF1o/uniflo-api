import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class PortalChallenge(SQLModel, table=True):
    """A mid-run request for values the portal delivered by email (UCT's OTP,
    Wits' temp-ID + password, UP's Application-ID + password), answered by the
    student via `POST /applications/{id}/challenge` while the run waits in place
    (`StudentRelaySource`). `supplied_values` is cleared as soon as the waiting
    run consumes it so secrets don't linger; `supplied_at` stays as the audit
    trail."""

    __tablename__ = "portal_challenges"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(
        foreign_key="applications.id", nullable=False, index=True
    )
    portal_slug: str = Field(nullable=False)
    # The field names the run is waiting for, e.g. ["otp"] or
    # ["temp_id", "password"] — the app renders one input per name.
    requested_fields: Any = Field(sa_column=Column(JSONB, nullable=False))
    supplied_values: Optional[Any] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    supplied_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
