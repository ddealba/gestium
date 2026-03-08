"""create person requests table"""

from alembic import op
import sqlalchemy as sa

revision = "c9d8e7f6a5b4"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("person_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("case_id", sa.String(length=36), nullable=True),
        sa.Column("employee_id", sa.String(length=36), nullable=True),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("resolution_type", sa.String(length=40), nullable=False),
        sa.Column("resolution_payload", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("resolved_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_person_requests_client_id", "person_requests", ["client_id"], unique=False)
    op.create_index("ix_person_requests_person_id", "person_requests", ["person_id"], unique=False)
    op.create_index("ix_person_requests_status", "person_requests", ["status"], unique=False)
    op.create_index("ix_person_requests_due_date", "person_requests", ["due_date"], unique=False)
    op.create_index("ix_person_requests_case_id", "person_requests", ["case_id"], unique=False)
    op.create_index("ix_person_requests_company_id", "person_requests", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_person_requests_company_id", table_name="person_requests")
    op.drop_index("ix_person_requests_case_id", table_name="person_requests")
    op.drop_index("ix_person_requests_due_date", table_name="person_requests")
    op.drop_index("ix_person_requests_status", table_name="person_requests")
    op.drop_index("ix_person_requests_person_id", table_name="person_requests")
    op.drop_index("ix_person_requests_client_id", table_name="person_requests")
    op.drop_table("person_requests")
