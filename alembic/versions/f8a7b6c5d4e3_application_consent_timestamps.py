"""applications: add popi/agreement consent timestamps

Records when the student explicitly accepted the portal's POPI notice and its
application agreement. The automation gate refuses to tick POPI / submit on the
student's behalf until the relevant timestamp is set. Both nullable + additive
(no backfill) — existing applications read as "not yet consented".

Revision ID: f8a7b6c5d4e3
Revises: e7f6a5b4c3d2
Create Date: 2026-06-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8a7b6c5d4e3"
down_revision: Union[str, Sequence[str], None] = "e7f6a5b4c3d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("popi_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("agreement_consent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("applications", "agreement_consent_at")
    op.drop_column("applications", "popi_consent_at")
