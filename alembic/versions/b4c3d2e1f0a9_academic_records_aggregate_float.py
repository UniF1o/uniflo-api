"""academic_records: aggregate -> Float, UNIQUE(student_id)

1. The server recomputes the aggregate as the unweighted mean of all subject
   marks rounded to one decimal (matching the frontend display). An Integer
   column truncates that, so widen it to double precision.
2. The API contract is one academic record per student (POST upserts). Back
   that invariant with a UNIQUE constraint instead of trusting app logic
   under concurrent writes. The table had no endpoint before this revision,
   so it is empty in every environment and the constraint applies cleanly.

Revision ID: b4c3d2e1f0a9
Revises: a3b2c1d4e5f6
Create Date: 2026-05-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4c3d2e1f0a9"
down_revision: Union[str, Sequence[str], None] = "a3b2c1d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_UNIQUE = "uq_academic_records_student_id"


def upgrade() -> None:
    op.alter_column(
        "academic_records",
        "aggregate",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=True,
        postgresql_using="aggregate::double precision",
    )
    op.create_unique_constraint(_UNIQUE, "academic_records", ["student_id"])


def downgrade() -> None:
    op.drop_constraint(_UNIQUE, "academic_records", type_="unique")
    op.alter_column(
        "academic_records",
        "aggregate",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="round(aggregate)::integer",
    )
