"""citizenship, subject_choices and guardian-consent fields on student_profiles

Additive and reversible. All columns nullable, no backfill:
- Phase 6: citizenship_status / passport_number / study_permit_type — the full
  residency taxonomy for non-SA-citizen (passport) applicants.
- Phase 7: subject_choices (chosen FET subject names, no marks, for Grade 10/11
  learners) + guardian_consent_at/by/relationship (POPIA minor consent).

Revision ID: d1e2f3a4b5c6
Revises: b7c653dd1cee
Create Date: 2026-07-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "b7c653dd1cee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student_profiles",
        sa.Column("citizenship_status", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column("passport_number", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column("study_permit_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column("subject_choices", JSONB(), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column("guardian_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column("guardian_consent_by", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column("guardian_relationship", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("student_profiles", "guardian_relationship")
    op.drop_column("student_profiles", "guardian_consent_by")
    op.drop_column("student_profiles", "guardian_consent_at")
    op.drop_column("student_profiles", "subject_choices")
    op.drop_column("student_profiles", "study_permit_type")
    op.drop_column("student_profiles", "passport_number")
    op.drop_column("student_profiles", "citizenship_status")
