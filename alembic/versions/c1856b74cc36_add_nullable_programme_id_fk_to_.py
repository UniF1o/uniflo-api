"""add nullable programme_id FK to applications and application_choices

Additive — two nullable UUID columns with FK to programmes. Reversible. No backfill.

Revision ID: c1856b74cc36
Revises: c3d2b1a4e5f6
Create Date: 2026-06-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1856b74cc36"
down_revision: Union[str, Sequence[str], None] = "c3d2b1a4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("programme_id", sa.Uuid(), nullable=True))
    op.create_index("ix_applications_programme_id", "applications", ["programme_id"], unique=False)
    op.create_foreign_key(
        "fk_applications_programme_id",
        "applications", "programmes",
        ["programme_id"], ["id"],
    )

    op.add_column("application_choices", sa.Column("programme_id", sa.Uuid(), nullable=True))
    op.create_index("ix_application_choices_programme_id", "application_choices", ["programme_id"], unique=False)
    op.create_foreign_key(
        "fk_application_choices_programme_id",
        "application_choices", "programmes",
        ["programme_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_application_choices_programme_id", "application_choices", type_="foreignkey")
    op.drop_index("ix_application_choices_programme_id", table_name="application_choices")
    op.drop_column("application_choices", "programme_id")

    op.drop_constraint("fk_applications_programme_id", "applications", type_="foreignkey")
    op.drop_index("ix_applications_programme_id", table_name="applications")
    op.drop_column("applications", "programme_id")
