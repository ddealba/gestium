"""Person request model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class PersonRequest(BaseModel):
    """Pending task/request assigned to a person."""

    __tablename__ = "person_requests"
    __table_args__ = (
        db.Index("ix_person_requests_client_person", "client_id", "person_id"),
        db.Index("ix_person_requests_client_status", "client_id", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    person_id = db.Column(db.String(36), db.ForeignKey("persons.id"), nullable=False, index=True)

    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=True, index=True)
    case_id = db.Column(db.String(36), db.ForeignKey("cases.id"), nullable=True, index=True)
    employee_id = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True, index=True)

    request_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, index=True, default="pending")
    due_date = db.Column(db.Date, nullable=True, index=True)

    resolution_type = db.Column(db.String(40), nullable=False, default="manual_review")
    resolution_payload = db.Column(db.JSON, nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    resolved_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    person = db.relationship("Person", backref=db.backref("requests", lazy="dynamic"))
    company = db.relationship("Company", backref=db.backref("person_requests", lazy="dynamic"))
    case = db.relationship("Case", backref=db.backref("person_requests", lazy="dynamic"))
    employee = db.relationship("Employee", backref=db.backref("person_requests", lazy="dynamic"))

    created_by_user = db.relationship("User", foreign_keys=[created_by])
    resolved_by_user = db.relationship("User", foreign_keys=[resolved_by])
