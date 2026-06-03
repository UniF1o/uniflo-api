"""phase 3: profile gap-fill columns + contacts + application_choices

Closes the portal-research data-model gaps (docs/phase-3/portal-research/
data-model-gaps.md):

1. student_profiles — adds the fields the four target portals capture that had
   no column: title/middle_names/maiden_name/preferred_name, a separate mailing
   (postal) address block, is_sa_citizen, disability_detail + assistance,
   current_activity/exam_number/sport, residence + funding intent, and the NBT
   reference block. All nullable (partial-upsert convention); none are added to
   the application-completeness guard.

2. contacts — new table for next-of-kin / fee-payer / guardian / emergency, one
   per type per student (UJ, Wits, UCT need these and we had nowhere to store
   them).

3. application_choices — every portal takes 2-3 ordered programme choices; a
   single applications.programme string wasn't enough.

Revision ID: e7f6a5b4c3d2
Revises: d6e5f4a3b2c1
Create Date: 2026-06-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f6a5b4c3d2"
down_revision: Union[str, Sequence[str], None] = "d6e5f4a3b2c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PROFILE_TEXT_COLUMNS = [
    "title",
    "middle_names",
    "maiden_name",
    "preferred_name",
    "mailing_street_address",
    "mailing_suburb",
    "mailing_city",
    "mailing_province",
    "disability_detail",
    "disability_assistance",
    "current_activity",
    "exam_number",
    "sport",
    "preferred_residence",
    "nbt_reference",
]


def upgrade() -> None:
    # 1. student_profiles new columns
    for name in _PROFILE_TEXT_COLUMNS:
        op.add_column("student_profiles", sa.Column(name, sa.Text(), nullable=True))
    op.add_column("student_profiles", sa.Column("mailing_postal_code", sa.String(4), nullable=True))
    op.add_column("student_profiles", sa.Column("mailing_same_as_residential", sa.Boolean(), nullable=True))
    op.add_column("student_profiles", sa.Column("is_sa_citizen", sa.Boolean(), nullable=True))
    op.add_column("student_profiles", sa.Column("wants_residence", sa.Boolean(), nullable=True))
    op.add_column("student_profiles", sa.Column("applying_nsfas", sa.Boolean(), nullable=True))
    op.add_column("student_profiles", sa.Column("applying_institutional_funding", sa.Boolean(), nullable=True))
    op.add_column("student_profiles", sa.Column("nbt_year", sa.Integer(), nullable=True))
    op.add_column("student_profiles", sa.Column("nbt_date", sa.Date(), nullable=True))
    op.add_column("student_profiles", sa.Column("redress_factors", postgresql.JSONB(), nullable=True))

    # 2. contacts
    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("contact_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("relationship", sa.Text(), nullable=True),
        sa.Column("id_number", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("street_address", sa.Text(), nullable=True),
        sa.Column("suburb", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("province", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "contact_type", name="uq_contacts_student_contact_type"
        ),
    )
    op.create_index(
        op.f("ix_contacts_student_id"), "contacts", ["student_id"], unique=False
    )

    # 3. application_choices
    op.create_table(
        "application_choices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("choice_number", sa.Integer(), nullable=False),
        sa.Column("programme", sa.Text(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id",
            "choice_number",
            name="uq_application_choices_application_choice",
        ),
    )
    op.create_index(
        op.f("ix_application_choices_application_id"),
        "application_choices",
        ["application_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_application_choices_application_id"),
        table_name="application_choices",
    )
    op.drop_table("application_choices")
    op.drop_index(op.f("ix_contacts_student_id"), table_name="contacts")
    op.drop_table("contacts")

    op.drop_column("student_profiles", "redress_factors")
    op.drop_column("student_profiles", "nbt_date")
    op.drop_column("student_profiles", "nbt_year")
    op.drop_column("student_profiles", "applying_institutional_funding")
    op.drop_column("student_profiles", "applying_nsfas")
    op.drop_column("student_profiles", "wants_residence")
    op.drop_column("student_profiles", "is_sa_citizen")
    op.drop_column("student_profiles", "mailing_same_as_residential")
    op.drop_column("student_profiles", "mailing_postal_code")
    for name in reversed(_PROFILE_TEXT_COLUMNS):
        op.drop_column("student_profiles", name)
