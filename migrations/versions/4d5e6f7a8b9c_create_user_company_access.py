"""create user_company_access table"""

from alembic import op
import sqlalchemy as sa

revision = "4d5e6f7a8b9c"
down_revision = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_company_access",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column(
            "access_level",
            sa.Enum("viewer", "operator", "manager", "admin", name="company_access_level"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "company_id", name="uq_user_company_access_user_company"),
    )
    op.create_index("ix_user_company_access_client_id", "user_company_access", ["client_id"], unique=False)
    op.create_index("ix_user_company_access_company_id", "user_company_access", ["company_id"], unique=False)
    op.create_index("ix_user_company_access_user_id", "user_company_access", ["user_id"], unique=False)
    op.create_index("ix_user_company_access_access_level", "user_company_access", ["access_level"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_company_access_access_level", table_name="user_company_access")
    op.drop_index("ix_user_company_access_user_id", table_name="user_company_access")
    op.drop_index("ix_user_company_access_company_id", table_name="user_company_access")
    op.drop_index("ix_user_company_access_client_id", table_name="user_company_access")
    op.drop_table("user_company_access")
    op.execute("DROP TYPE IF EXISTS company_access_level")
