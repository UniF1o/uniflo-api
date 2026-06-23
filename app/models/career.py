import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Career(SQLModel, table=True):
    __tablename__ = "careers"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(nullable=False, unique=True, index=True)
    title: str = Field(nullable=False)
    industry: str = Field(nullable=False, index=True)
    description: str = Field(nullable=False)
    # {entry, mid, senior, currency: "ZAR", period: "month", display}
    compensation: Any = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    # {demand, outlook, pathways: [...], employment_note}
    employability: Any = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    # {all_of: [...], any_of: [...]} — canonical NSC subject names
    subject_rule: Any = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    # Subjects that strengthen the path but don't gate it (the "+rec" subjects)
    recommended_subjects: Optional[Any] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    # Tokens matched word-aware against programme names to find related degrees
    programme_keywords: Any = Field(
        default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]")
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=True,
        ),
    )
