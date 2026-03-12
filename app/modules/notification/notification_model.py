"""Notification model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Notification(BaseModel):
    """Internal notification/alert for portal or backoffice users."""

    __tablename__ = "notifications"
    __table_args__ = (
        db.Index("ix_notifications_client_channel", "client_id", "channel"),
        db.Index("ix_notifications_client_user", "client_id", "user_id"),
        db.Index("ix_notifications_client_person", "client_id", "person_id"),
        db.Index("ix_notifications_client_status", "client_id", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)
    person_id = db.Column(db.String(36), db.ForeignKey("persons.id"), nullable=True, index=True)

    channel = db.Column(db.String(40), nullable=False, index=True)
    notification_type = db.Column(db.String(60), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)

    entity_type = db.Column(db.String(60), nullable=True)
    entity_id = db.Column(db.String(36), nullable=True, index=True)

    status = db.Column(db.String(20), nullable=False, default="unread", index=True)
    priority = db.Column(db.String(20), nullable=False, default="medium", index=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    person = db.relationship("Person", foreign_keys=[person_id])
