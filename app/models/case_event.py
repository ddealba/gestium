"""Case event model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db


class CaseEvent(db.Model):
    """Represents an event in the lifecycle of a case."""

    __tablename__ = "case_events"
    __table_args__ = (
        db.Index("ix_case_events_client_case_created_at", "client_id", "case_id", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    case_id = db.Column(db.String(36), db.ForeignKey("cases.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False, index=True)
    actor_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)
    event_type = db.Column(
        db.Enum("comment", "status_change", "assignment", "attachment", name="case_event_type"),
        nullable=False,
    )
    payload = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    case = db.relationship("Case", backref=db.backref("events", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<CaseEvent id={id} client_id={client_id} case_id={case_id} "
            "event_type={event_type}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            case_id=self.case_id,
            event_type=self.event_type,
        )
