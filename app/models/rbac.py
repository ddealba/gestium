"""RBAC association tables."""

from __future__ import annotations

from app.extensions import db

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.String(36), db.ForeignKey("roles.id"), nullable=False),
    db.Column("permission_id", db.String(36), db.ForeignKey("permissions.id"), nullable=False),
    db.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
)

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.String(36), db.ForeignKey("users.id"), nullable=False),
    db.Column("role_id", db.String(36), db.ForeignKey("roles.id"), nullable=False),
    db.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
)
