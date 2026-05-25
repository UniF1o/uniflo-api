"""student_profiles: split address + add religion/disability/marital_status/ethnicity

1. The single `address` column is replaced by five sub-fields so Playwright
   adapters can map each piece to the corresponding portal input independently.
   All new address columns are nullable (matching the partial-upsert convention
   from a3b2c1d4e5f6); the application completeness check enforces the required
   subset at submission time.

2. Four demographic fields are added as TEXT NULLABLE. They are nullable to
   avoid a backfill requirement on existing rows; the completeness guard in
   create_application ensures they are present before an application is
   submitted.

Revision ID: c5d4e3f2a1b0
Revises: b4c3d2e1f0a9
Create Date: 2026-05-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5d4e3f2a1b0"
down_revision: Union[str, Sequence[str], None] = "b4c3d2e1f0a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # address split
    op.add_column("student_profiles", sa.Column("street_address", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("suburb", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("city", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("province", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("postal_code", sa.String(4), nullable=True))
    op.drop_column("student_profiles", "address")

    # new demographic fields
    op.add_column("student_profiles", sa.Column("religion", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("disability", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("marital_status", sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("ethnicity", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("student_profiles", "ethnicity")
    op.drop_column("student_profiles", "marital_status")
    op.drop_column("student_profiles", "disability")
    op.drop_column("student_profiles", "religion")
    op.add_column("student_profiles", sa.Column("address", sa.Text(), nullable=True))
    op.drop_column("student_profiles", "postal_code")
    op.drop_column("student_profiles", "province")
    op.drop_column("student_profiles", "city")
    op.drop_column("student_profiles", "suburb")
    op.drop_column("student_profiles", "street_address")
