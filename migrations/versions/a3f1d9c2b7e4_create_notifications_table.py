"""create notifications table"""

from alembic import op
import sqlalchemy as sa

revision = "a3f1d9c2b7e4"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("person_id", sa.String(length=36), nullable=True),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("notification_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_client_channel", "notifications", ["client_id", "channel"])
    op.create_index("ix_notifications_client_user", "notifications", ["client_id", "user_id"])
    op.create_index("ix_notifications_client_person", "notifications", ["client_id", "person_id"])
    op.create_index("ix_notifications_client_status", "notifications", ["client_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_notifications_client_status", table_name="notifications")
    op.drop_index("ix_notifications_client_person", table_name="notifications")
    op.drop_index("ix_notifications_client_user", table_name="notifications")
    op.drop_index("ix_notifications_client_channel", table_name="notifications")
    op.drop_table("notifications")
