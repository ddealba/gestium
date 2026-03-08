"""add person and employee to documents

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-03-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("person_id", sa.String(length=36), nullable=True))
    op.add_column("documents", sa.Column("employee_id", sa.String(length=36), nullable=True))

    op.create_foreign_key("fk_documents_person_id", "documents", "persons", ["person_id"], ["id"])
    op.create_foreign_key("fk_documents_employee_id", "documents", "employees", ["employee_id"], ["id"])

    op.create_index("ix_documents_person_id", "documents", ["person_id"], unique=False)
    op.create_index("ix_documents_employee_id", "documents", ["employee_id"], unique=False)
    op.create_index(
        "ix_documents_client_person_employee",
        "documents",
        ["client_id", "person_id", "employee_id"],
        unique=False,
    )

    op.alter_column("documents", "company_id", existing_type=sa.String(length=36), nullable=True)
    op.alter_column("documents", "case_id", existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    op.alter_column("documents", "case_id", existing_type=sa.String(length=36), nullable=False)
    op.alter_column("documents", "company_id", existing_type=sa.String(length=36), nullable=False)

    op.drop_index("ix_documents_client_person_employee", table_name="documents")
    op.drop_index("ix_documents_employee_id", table_name="documents")
    op.drop_index("ix_documents_person_id", table_name="documents")

    op.drop_constraint("fk_documents_employee_id", "documents", type_="foreignkey")
    op.drop_constraint("fk_documents_person_id", "documents", type_="foreignkey")

    op.drop_column("documents", "employee_id")
    op.drop_column("documents", "person_id")
