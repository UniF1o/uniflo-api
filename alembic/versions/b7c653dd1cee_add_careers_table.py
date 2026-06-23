"""add careers table

New `careers` catalogue table — curated static data seeded by
scripts/seed_careers.py. Additive and reversible. No foreign keys to
other tables (careers link to programmes only at query time via
programme_keywords, not as a DB constraint).

Revision ID: b7c653dd1cee
Revises: c1856b74cc36
Create Date: 2026-06-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b7c653dd1cee"
down_revision: Union[str, Sequence[str], None] = "c1856b74cc36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "careers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("compensation", JSONB(), nullable=False, server_default="{}"),
        sa.Column("employability", JSONB(), nullable=False, server_default="{}"),
        sa.Column("subject_rule", JSONB(), nullable=False, server_default="{}"),
        sa.Column("recommended_subjects", JSONB(), nullable=True),
        sa.Column("programme_keywords", JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_careers_slug", "careers", ["slug"], unique=True)
    op.create_index("ix_careers_industry", "careers", ["industry"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_careers_industry", table_name="careers")
    op.drop_index("ix_careers_slug", table_name="careers")
    op.drop_table("careers")
