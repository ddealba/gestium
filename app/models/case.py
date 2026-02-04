"""Case model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Case(BaseModel):
    """Represents a case belonging to a company."""

    __tablename__ = "cases"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)

    company = db.relationship("Company", backref=db.backref("cases", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            f"<Case id={self.id} client_id={self.client_id} "
            f"company_id={self.company_id} title={self.title}>"
        )
