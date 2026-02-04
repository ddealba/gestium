"""create companies table"""

from alembic import op
import sqlalchemy as sa

revision = "5e6f7a8b9c0d"
down_revision = "4d5e6f7a8b9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tax_id", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="company_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.UniqueConstraint("client_id", "tax_id", name="uq_companies_client_tax_id"),
    )
    op.create_index("ix_companies_client_id", "companies", ["client_id"], unique=False)
    op.create_index("ix_companies_tax_id", "companies", ["tax_id"], unique=False)
    op.create_index("ix_companies_status", "companies", ["status"], unique=False)
    op.create_index("ix_companies_client_status", "companies", ["client_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_companies_client_status", table_name="companies")
    op.drop_index("ix_companies_status", table_name="companies")
    op.drop_index("ix_companies_tax_id", table_name="companies")
    op.drop_index("ix_companies_client_id", table_name="companies")
    op.drop_table("companies")
    op.execute("DROP TYPE IF EXISTS company_status")
