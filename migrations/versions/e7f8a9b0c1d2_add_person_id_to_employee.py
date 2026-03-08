"""add person_id to employee

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-03-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c1d2"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("person_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_employees_person_id_persons",
        "employees",
        "persons",
        ["person_id"],
        ["id"],
    )
    op.create_index("ix_employees_person_id", "employees", ["person_id"], unique=False)
    op.create_index(
        "ix_employees_client_company_person",
        "employees",
        ["client_id", "company_id", "person_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_employees_client_company_person", table_name="employees")
    op.drop_index("ix_employees_person_id", table_name="employees")
    op.drop_constraint("fk_employees_person_id_persons", "employees", type_="foreignkey")
    op.drop_column("employees", "person_id")
