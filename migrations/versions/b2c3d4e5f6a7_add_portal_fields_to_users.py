"""add portal fields to users

Revision ID: b2c3d4e5f6a7
Revises: a9b8c7d6e5f4
Create Date: 2026-03-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None


user_type_enum = sa.Enum("internal", "portal", name="user_type")


def upgrade() -> None:
    bind = op.get_bind()
    user_type_enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column("user_type", user_type_enum, nullable=False, server_default="internal"),
    )
    op.add_column("users", sa.Column("person_id", sa.String(length=36), nullable=True))

    op.create_foreign_key("fk_users_person_id", "users", "persons", ["person_id"], ["id"])
    op.create_index("ix_users_user_type", "users", ["user_type"], unique=False)
    op.create_index("ix_users_person_id", "users", ["person_id"], unique=False)

    op.execute("UPDATE users SET user_type = 'internal' WHERE user_type IS NULL")
    op.alter_column("users", "user_type", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_users_person_id", table_name="users")
    op.drop_index("ix_users_user_type", table_name="users")
    op.drop_constraint("fk_users_person_id", "users", type_="foreignkey")

    op.drop_column("users", "person_id")
    op.drop_column("users", "user_type")

    bind = op.get_bind()
    user_type_enum.drop(bind, checkfirst=True)
