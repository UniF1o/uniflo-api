"""add programmes.qualification_type and programmes.duration_years

Additive — two nullable columns on programmes. Reversible.

Revision ID: e2a1c4b6d8f0
Revises: 7bd16112db5c
Create Date: 2026-06-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2a1c4b6d8f0"
down_revision: Union[str, Sequence[str], None] = "7bd16112db5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "programmes",
        sa.Column("qualification_type", sa.String(), nullable=True),
    )
    op.add_column(
        "programmes",
        sa.Column("duration_years", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("programmes", "duration_years")
    op.drop_column("programmes", "qualification_type")
