"""academic_records: add record_type, replace single-column unique with composite

Replaces UNIQUE(student_id) with UNIQUE(student_id, record_type) so each
student can hold at most one record per type (grade_11_final, grade_12_april).
Existing rows are backfilled to record_type='grade_11_final' via server_default.

Revision ID: d6e5f4a3b2c1
Revises: c5d4e3f2a1b0
Create Date: 2026-05-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6e5f4a3b2c1"
down_revision: Union[str, Sequence[str], None] = "c5d4e3f2a1b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_UNIQUE = "uq_academic_records_student_id"
_NEW_UNIQUE = "uq_academic_records_student_record_type"


def upgrade() -> None:
    op.drop_constraint(_OLD_UNIQUE, "academic_records", type_="unique")
    op.add_column(
        "academic_records",
        sa.Column(
            "record_type",
            sa.Text(),
            nullable=False,
            server_default="grade_11_final",
        ),
    )
    op.create_unique_constraint(
        _NEW_UNIQUE, "academic_records", ["student_id", "record_type"]
    )


def downgrade() -> None:
    op.drop_constraint(_NEW_UNIQUE, "academic_records", type_="unique")
    op.drop_column("academic_records", "record_type")
    op.create_unique_constraint(_OLD_UNIQUE, "academic_records", ["student_id"])
