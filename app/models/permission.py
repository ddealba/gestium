"""Permission model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel
from app.models.rbac import role_permissions


class Permission(BaseModel):
    """Represents a permission that can be assigned to roles."""

    __tablename__ = "permissions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = db.Column(db.String(128), nullable=False, unique=True, index=True)
    description = db.Column(db.String(255), nullable=True)

    roles = db.relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission id={self.id} code={self.code}>"
