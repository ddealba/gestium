"""Document model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Document(BaseModel):
    """Represents a document belonging to a company."""

    __tablename__ = "documents"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)

    company = db.relationship("Company", backref=db.backref("documents", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} client_id={self.client_id} "
            f"company_id={self.company_id} filename={self.filename}>"
        )
