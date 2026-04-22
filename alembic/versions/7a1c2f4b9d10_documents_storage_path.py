"""documents: replace storage_url with storage_path

Revision ID: 7a1c2f4b9d10
Revises: 4dee565d63cb
Create Date: 2026-04-22 10:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "7a1c2f4b9d10"
down_revision: Union[str, Sequence[str], None] = "4dee565d63cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the cached public URL with the storage path we regenerate signed URLs from."""
    op.add_column(
        "documents",
        sa.Column(
            "storage_path",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    # Drop the server default — new rows must supply storage_path explicitly.
    op.alter_column("documents", "storage_path", server_default=None)
    op.drop_column("documents", "storage_url")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "storage_url",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("documents", "storage_url", server_default=None)
    op.drop_column("documents", "storage_path")
