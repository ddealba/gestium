"""create persons table"""

from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "persons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("document_number", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "pending_info", "active", "inactive", name="person_status"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "email", name="uq_persons_client_email"),
    )
    op.create_index("ix_persons_client_id", "persons", ["client_id"], unique=False)
    op.create_index("ix_persons_email", "persons", ["email"], unique=False)
    op.create_index("ix_persons_document_number", "persons", ["document_number"], unique=False)
    op.create_index("ix_persons_created_by", "persons", ["created_by"], unique=False)
    op.create_index("ix_persons_client_document", "persons", ["client_id", "document_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_persons_client_document", table_name="persons")
    op.drop_index("ix_persons_created_by", table_name="persons")
    op.drop_index("ix_persons_document_number", table_name="persons")
    op.drop_index("ix_persons_email", table_name="persons")
    op.drop_index("ix_persons_client_id", table_name="persons")
    op.drop_table("persons")
    op.execute("DROP TYPE IF EXISTS person_status")
