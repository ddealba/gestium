"""create person company relations table"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_company_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("person_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column(
            "relation_type",
            sa.Enum("owner", "employee", "other", name="person_company_relation_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="person_company_relation_status"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_pcr_client_id", "person_company_relations", ["client_id"], unique=False)
    op.create_index("ix_pcr_person_id", "person_company_relations", ["person_id"], unique=False)
    op.create_index("ix_pcr_company_id", "person_company_relations", ["company_id"], unique=False)
    op.create_index("ix_pcr_relation_type", "person_company_relations", ["relation_type"], unique=False)
    op.create_index("ix_pcr_status", "person_company_relations", ["status"], unique=False)
    op.create_index(
        "uq_pcr_active_person_company_type",
        "person_company_relations",
        ["client_id", "person_id", "company_id", "relation_type"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_pcr_active_person_company_type", table_name="person_company_relations")
    op.drop_index("ix_pcr_status", table_name="person_company_relations")
    op.drop_index("ix_pcr_relation_type", table_name="person_company_relations")
    op.drop_index("ix_pcr_company_id", table_name="person_company_relations")
    op.drop_index("ix_pcr_person_id", table_name="person_company_relations")
    op.drop_index("ix_pcr_client_id", table_name="person_company_relations")
    op.drop_table("person_company_relations")
    op.execute("DROP TYPE IF EXISTS person_company_relation_status")
    op.execute("DROP TYPE IF EXISTS person_company_relation_type")
