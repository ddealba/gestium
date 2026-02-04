"""User model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class User(BaseModel):
    """Represents a user within a tenant."""

    __tablename__ = "users"
    __table_args__ = (
        db.UniqueConstraint("client_id", "email", name="uq_users_client_email"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum("invited", "active", "disabled", name="user_status"),
        nullable=False,
        index=True,
        default="invited",
    )

    client = db.relationship("Client", backref=db.backref("users", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<User id={self.id} client_id={self.client_id} email={self.email} status={self.status}>"
