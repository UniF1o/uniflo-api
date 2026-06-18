"""add faculties and programmes tables, universities.scoring_method

Additive — two new tables and one nullable column. Reversible.

Revision ID: 7bd16112db5c
Revises: c2d1e0f9a8b7
Create Date: 2026-06-18 17:27:39.409408

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7bd16112db5c"
down_revision: Union[str, Sequence[str], None] = "c2d1e0f9a8b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faculties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("close_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_faculties_university_id", "faculties", ["university_id"], unique=False
    )

    op.create_table(
        "programmes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("university_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("qualification_code", sa.String(), nullable=True),
        sa.Column("intake_year", sa.Integer(), nullable=False),
        sa.Column("min_aps", sa.Integer(), nullable=True),
        sa.Column(
            "requirements",
            postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculties.id"]),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_programmes_university_id", "programmes", ["university_id"], unique=False
    )
    op.create_index(
        "ix_programmes_faculty_id", "programmes", ["faculty_id"], unique=False
    )

    op.add_column(
        "universities",
        sa.Column("scoring_method", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("universities", "scoring_method")
    op.drop_index("ix_programmes_faculty_id", table_name="programmes")
    op.drop_index("ix_programmes_university_id", table_name="programmes")
    op.drop_table("programmes")
    op.drop_index("ix_faculties_university_id", table_name="faculties")
    op.drop_table("faculties")
