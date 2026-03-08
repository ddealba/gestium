"""User model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel
from app.models.rbac import user_roles


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
    user_type = db.Column(
        db.Enum("internal", "portal", name="user_type"),
        nullable=False,
        index=True,
        default="internal",
    )
    person_id = db.Column(db.String(36), db.ForeignKey("persons.id"), nullable=True, index=True)

    client = db.relationship("Client", backref=db.backref("users", lazy="dynamic"))
    person = db.relationship(
        "Person",
        foreign_keys=[person_id],
        backref=db.backref("portal_users", lazy="dynamic"),
    )
    roles = db.relationship("Role", secondary=user_roles, back_populates="users")

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} client_id={self.client_id} email={self.email} "
            f"status={self.status} user_type={self.user_type} person_id={self.person_id}>"
        )
