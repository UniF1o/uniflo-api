"""add programmes.combination (major-combination metadata)

Additive — one nullable JSONB column on programmes. Reversible.

Revision ID: c3d2b1a4e5f6
Revises: e2a1c4b6d8f0
Create Date: 2026-06-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d2b1a4e5f6"
down_revision: Union[str, Sequence[str], None] = "e2a1c4b6d8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "programmes",
        sa.Column("combination", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("programmes", "combination")
