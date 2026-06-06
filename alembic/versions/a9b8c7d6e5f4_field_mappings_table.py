"""create field_mappings table

The AI-proposed profile→portal mapping per application, for Partner-A's review
screen (renders the entries + flags the low-confidence ones). One row per
application (unique application_id, upserted on regenerate). Additive — new table.

Revision ID: a9b8c7d6e5f4
Revises: f8a7b6c5d4e3
Create Date: 2026-06-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "f8a7b6c5d4e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "field_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entries", postgresql.JSONB(), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=False),
        sa.Column("confidence_threshold", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_field_mappings_application_id"),
    )
    op.create_index(
        "ix_field_mappings_application_id", "field_mappings", ["application_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_field_mappings_application_id", table_name="field_mappings")
    op.drop_table("field_mappings")
