"""create rbac tables"""

from alembic import op
import sqlalchemy as sa

revision = "3c4d5e6f7a8b"
down_revision = "2b3c4d5e6f7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.Enum("platform", "tenant", name="role_scope"), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(scope = 'tenant' AND client_id IS NOT NULL) OR "
            "(scope = 'platform' AND client_id IS NULL)",
            name="ck_roles_scope_client_id",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_client_id", "roles", ["client_id"], unique=False)
    op.create_index("ix_roles_scope", "roles", ["scope"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("permission_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_index("ix_roles_scope", table_name="roles")
    op.drop_index("ix_roles_client_id", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")
