"""create document extractions table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ad1e2f3a4b5c"
down_revision = "9c0d1e2f3a4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_extractions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column(
            "extracted_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("success", "failed", "partial", name="document_extraction_status"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_document_extractions_case_id", "document_extractions", ["case_id"], unique=False)
    op.create_index("ix_document_extractions_client_id", "document_extractions", ["client_id"], unique=False)
    op.create_index("ix_document_extractions_company_id", "document_extractions", ["company_id"], unique=False)
    op.create_index(
        "ix_document_extractions_created_by_user_id",
        "document_extractions",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index("ix_document_extractions_document_id", "document_extractions", ["document_id"], unique=False)
    op.create_index("ix_document_extractions_status", "document_extractions", ["status"], unique=False)
    op.create_index(
        "ix_document_extractions_client_document_created_at",
        "document_extractions",
        ["client_id", "document_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_extractions_client_company_created_at",
        "document_extractions",
        ["client_id", "company_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_extractions_client_status",
        "document_extractions",
        ["client_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_extractions_client_status", table_name="document_extractions")
    op.drop_index("ix_document_extractions_client_company_created_at", table_name="document_extractions")
    op.drop_index("ix_document_extractions_client_document_created_at", table_name="document_extractions")
    op.drop_index("ix_document_extractions_status", table_name="document_extractions")
    op.drop_index("ix_document_extractions_document_id", table_name="document_extractions")
    op.drop_index("ix_document_extractions_created_by_user_id", table_name="document_extractions")
    op.drop_index("ix_document_extractions_company_id", table_name="document_extractions")
    op.drop_index("ix_document_extractions_client_id", table_name="document_extractions")
    op.drop_index("ix_document_extractions_case_id", table_name="document_extractions")
    op.drop_table("document_extractions")

    op.execute("DROP TYPE IF EXISTS document_extraction_status")
