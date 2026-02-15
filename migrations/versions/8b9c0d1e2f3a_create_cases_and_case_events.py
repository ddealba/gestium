"""create cases and case_events tables"""

from alembic import op
import sqlalchemy as sa

revision = "8b9c0d1e2f3a"
down_revision = "7a8b9c0d1e2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "in_progress", "waiting", "done", "cancelled", name="case_status"),
            nullable=False,
        ),
        sa.Column("responsible_user_id", sa.String(length=36), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cases_client_id", "cases", ["client_id"], unique=False)
    op.create_index("ix_cases_company_id", "cases", ["company_id"], unique=False)
    op.create_index("ix_cases_status", "cases", ["status"], unique=False)
    op.create_index("ix_cases_responsible_user_id", "cases", ["responsible_user_id"], unique=False)
    op.create_index("ix_cases_due_date", "cases", ["due_date"], unique=False)
    op.create_index("ix_cases_client_company_status", "cases", ["client_id", "company_id", "status"], unique=False)
    op.create_index("ix_cases_client_due_date", "cases", ["client_id", "due_date"], unique=False)

    op.create_table(
        "case_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "event_type",
            sa.Enum("comment", "status_change", "assignment", "attachment", name="case_event_type"),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_events_client_id", "case_events", ["client_id"], unique=False)
    op.create_index("ix_case_events_case_id", "case_events", ["case_id"], unique=False)
    op.create_index("ix_case_events_company_id", "case_events", ["company_id"], unique=False)
    op.create_index("ix_case_events_actor_user_id", "case_events", ["actor_user_id"], unique=False)
    op.create_index(
        "ix_case_events_client_case_created_at",
        "case_events",
        ["client_id", "case_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_case_events_client_case_created_at", table_name="case_events")
    op.drop_index("ix_case_events_actor_user_id", table_name="case_events")
    op.drop_index("ix_case_events_company_id", table_name="case_events")
    op.drop_index("ix_case_events_case_id", table_name="case_events")
    op.drop_index("ix_case_events_client_id", table_name="case_events")
    op.drop_table("case_events")

    op.drop_index("ix_cases_client_due_date", table_name="cases")
    op.drop_index("ix_cases_client_company_status", table_name="cases")
    op.drop_index("ix_cases_due_date", table_name="cases")
    op.drop_index("ix_cases_responsible_user_id", table_name="cases")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_company_id", table_name="cases")
    op.drop_index("ix_cases_client_id", table_name="cases")
    op.drop_table("cases")

    op.execute("DROP TYPE IF EXISTS case_event_type")
    op.execute("DROP TYPE IF EXISTS case_status")
