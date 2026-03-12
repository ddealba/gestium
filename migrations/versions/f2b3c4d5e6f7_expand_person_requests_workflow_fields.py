"""expand person requests workflow fields"""

from alembic import op
import sqlalchemy as sa

revision = "f2b3c4d5e6f7"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("person_requests", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column("person_requests", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("person_requests", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("person_requests", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("person_requests", "reviewed_at")
    op.drop_column("person_requests", "submitted_at")
    op.drop_column("person_requests", "rejection_reason")
    op.drop_column("person_requests", "review_notes")
