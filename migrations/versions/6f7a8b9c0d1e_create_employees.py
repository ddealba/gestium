"""create employees table"""

from alembic import op
import sqlalchemy as sa

revision = "6f7a8b9c0d1e"
down_revision = "5e6f7a8b9c0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("employee_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "terminated", name="employee_status"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(status = 'terminated' AND end_date IS NOT NULL AND end_date >= start_date) "
            "OR (status = 'active' AND end_date IS NULL)",
            name="ck_employees_status_dates",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_employees_client_id", "employees", ["client_id"], unique=False)
    op.create_index("ix_employees_company_id", "employees", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_employees_company_id", table_name="employees")
    op.drop_index("ix_employees_client_id", table_name="employees")
    op.drop_table("employees")
    op.execute("DROP TYPE IF EXISTS employee_status")
