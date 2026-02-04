"""Role model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel
from app.models.rbac import role_permissions, user_roles


class Role(BaseModel):
    """Represents a role that groups permissions."""

    __tablename__ = "roles"
    __table_args__ = (
        db.CheckConstraint(
            "(scope = 'tenant' AND client_id IS NOT NULL) OR "
            "(scope = 'platform' AND client_id IS NULL)",
            name="ck_roles_scope_client_id",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    scope = db.Column(
        db.Enum("platform", "tenant", name="role_scope"),
        nullable=False,
        index=True,
    )
    client_id = db.Column(
        db.String(36),
        db.ForeignKey("clients.id"),
        nullable=True,
        index=True,
    )

    permissions = db.relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )
    users = db.relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name} scope={self.scope} client_id={self.client_id}>"
