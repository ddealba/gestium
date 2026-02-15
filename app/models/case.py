"""Case model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Case(BaseModel):
    """Represents a case belonging to a company."""

    __tablename__ = "cases"
    __table_args__ = (
        db.Index("ix_cases_client_company_status", "client_id", "company_id", "status"),
        db.Index("ix_cases_client_due_date", "client_id", "due_date"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False, index=True)
    type = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum("open", "in_progress", "waiting", "done", "cancelled", name="case_status"),
        nullable=False,
        index=True,
        default="open",
    )
    responsible_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)
    due_date = db.Column(db.Date, nullable=True, index=True)

    company = db.relationship("Company", backref=db.backref("cases", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<Case id={id} client_id={client_id} company_id={company_id} "
            "type={type} title={title} status={status}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            company_id=self.company_id,
            type=self.type,
            title=self.title,
            status=self.status,
        )
