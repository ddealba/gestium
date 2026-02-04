"""User invitation model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class UserInvitation(BaseModel):
    """Represents a tenant-scoped user invitation."""

    __tablename__ = "user_invitations"
    __table_args__ = (
        db.Index("ix_user_invitations_client_email", "client_id", "email"),
        db.Index("ix_user_invitations_expires_at", "expires_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    client = db.relationship("Client", backref=db.backref("user_invitations", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<UserInvitation id={id} client_id={client_id} email={email} expires_at={expires_at} "
            "used_at={used_at}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            email=self.email,
            expires_at=self.expires_at,
            used_at=self.used_at,
        )
