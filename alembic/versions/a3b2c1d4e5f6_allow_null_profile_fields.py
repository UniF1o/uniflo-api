"""student_profiles: allow null on all profile fields for partial upsert

Revision ID: a3b2c1d4e5f6
Revises: 7a1c2f4b9d10
Create Date: 2026-05-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "a3b2c1d4e5f6"
down_revision: Union[str, Sequence[str], None] = "5f641ecfb811"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = [
    ("first_name", sqlmodel.sql.sqltypes.AutoString()),
    ("last_name", sqlmodel.sql.sqltypes.AutoString()),
    ("id_number", sqlmodel.sql.sqltypes.AutoString()),
    ("date_of_birth", sa.Date()),
    ("phone", sqlmodel.sql.sqltypes.AutoString()),
    ("address", sqlmodel.sql.sqltypes.AutoString()),
    ("nationality", sqlmodel.sql.sqltypes.AutoString()),
    ("gender", sqlmodel.sql.sqltypes.AutoString()),
    ("home_language", sqlmodel.sql.sqltypes.AutoString()),
]


def upgrade() -> None:
    for col, type_ in _COLS:
        op.alter_column("student_profiles", col, nullable=True, existing_type=type_)


def downgrade() -> None:
    for col, type_ in _COLS:
        op.alter_column("student_profiles", col, nullable=False, existing_type=type_)
