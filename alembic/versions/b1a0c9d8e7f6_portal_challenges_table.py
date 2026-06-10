"""create portal_challenges table

A mid-run request for values a portal delivered by email (UCT OTP, Wits temp-ID
+ password, UP Application-ID + password), answered by the student via
POST /applications/{id}/challenge while the automation run waits in place.
supplied_values is cleared once consumed (supplied_at stays as audit).
Additive — new table.

Revision ID: b1a0c9d8e7f6
Revises: a9b8c7d6e5f4
Create Date: 2026-06-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b1a0c9d8e7f6"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portal_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portal_slug", sa.String(), nullable=False),
        sa.Column("requested_fields", postgresql.JSONB(), nullable=False),
        sa.Column("supplied_values", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_portal_challenges_application_id",
        "portal_challenges",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_portal_challenges_application_id", table_name="portal_challenges"
    )
    op.drop_table("portal_challenges")
