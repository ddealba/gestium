"""create documents table"""

from alembic import op
import sqlalchemy as sa

revision = "9c0d1e2f3a4b"
down_revision = "8b9c0d1e2f3a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("doc_type", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "processed", "archived", name="document_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"], unique=False)
    op.create_index("ix_documents_client_id", "documents", ["client_id"], unique=False)
    op.create_index("ix_documents_company_id", "documents", ["company_id"], unique=False)
    op.create_index("ix_documents_uploaded_by_user_id", "documents", ["uploaded_by_user_id"], unique=False)
    op.create_index("ix_documents_status", "documents", ["status"], unique=False)
    op.create_index(
        "ix_documents_client_company_case",
        "documents",
        ["client_id", "company_id", "case_id"],
        unique=False,
    )
    op.create_index("ix_documents_client_status", "documents", ["client_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_client_status", table_name="documents")
    op.drop_index("ix_documents_client_company_case", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_uploaded_by_user_id", table_name="documents")
    op.drop_index("ix_documents_company_id", table_name="documents")
    op.drop_index("ix_documents_client_id", table_name="documents")
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_table("documents")

    op.execute("DROP TYPE IF EXISTS document_status")
