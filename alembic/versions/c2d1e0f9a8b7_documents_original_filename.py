"""documents: add original_filename

Stores the user-supplied upload name for display only (storage paths stay
UUID-based). Nullable and additive — existing rows keep NULL, the app treats a
missing name as "unknown" and the frontend falls back to the upload timestamp.

Revision ID: c2d1e0f9a8b7
Revises: b1a0c9d8e7f6
Create Date: 2026-06-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2d1e0f9a8b7"
down_revision: Union[str, Sequence[str], None] = "b1a0c9d8e7f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("original_filename", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "original_filename")
