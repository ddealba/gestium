"""add company fk to user_company_access"""

from alembic import op

revision = "7a8b9c0d1e2f"
down_revision = "6f7a8b9c0d1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_company_access") as batch_op:
        batch_op.create_foreign_key(
            "fk_user_company_access_company_id",
            "companies",
            ["company_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_user_company_access_client_user",
            ["client_id", "user_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("user_company_access") as batch_op:
        batch_op.drop_index("ix_user_company_access_client_user")
        batch_op.drop_constraint("fk_user_company_access_company_id", type_="foreignkey")
