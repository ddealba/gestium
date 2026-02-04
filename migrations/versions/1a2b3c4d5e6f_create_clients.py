"""create clients table"""

from alembic import op
import sqlalchemy as sa

revision = "1a2b3c4d5e6f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "suspended", "disabled", name="client_status"),
            nullable=False,
        ),
        sa.Column("plan", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_clients_status", "clients", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clients_status", table_name="clients")
    op.drop_table("clients")
