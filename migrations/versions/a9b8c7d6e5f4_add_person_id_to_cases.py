"""add person_id to cases"""

from alembic import op
import sqlalchemy as sa


revision = "a9b8c7d6e5f4"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("person_id", sa.String(length=36), nullable=True))
    op.create_index("ix_cases_person_id", "cases", ["person_id"], unique=False)
    op.create_index(
        "ix_cases_client_person_status",
        "cases",
        ["client_id", "person_id", "status"],
        unique=False,
    )
    op.create_foreign_key("fk_cases_person_id_persons", "cases", "persons", ["person_id"], ["id"])

    with op.batch_alter_table("cases") as batch_op:
        batch_op.alter_column("company_id", existing_type=sa.String(length=36), nullable=True)

    with op.batch_alter_table("case_events") as batch_op:
        batch_op.alter_column("company_id", existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("case_events") as batch_op:
        batch_op.alter_column("company_id", existing_type=sa.String(length=36), nullable=False)

    with op.batch_alter_table("cases") as batch_op:
        batch_op.alter_column("company_id", existing_type=sa.String(length=36), nullable=False)

    op.drop_constraint("fk_cases_person_id_persons", "cases", type_="foreignkey")
    op.drop_index("ix_cases_client_person_status", table_name="cases")
    op.drop_index("ix_cases_person_id", table_name="cases")
    op.drop_column("cases", "person_id")
