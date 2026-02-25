"""Audit log model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class AuditLog(db.Model):
    """Immutable audit trail entries for tenant-scoped critical actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        db.Index("ix_audit_logs_client_id", "client_id"),
        db.Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False)
    actor_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.String(36), nullable=False)
    metadata_json = db.Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    client = db.relationship("Client", backref=db.backref("audit_logs", lazy="dynamic"))
    actor_user = db.relationship("User", backref=db.backref("audit_logs", lazy="dynamic"))
